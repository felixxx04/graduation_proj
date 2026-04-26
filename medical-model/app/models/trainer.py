"""DeepFM 训练器 — FocalLoss + DP-SGD(Opacus) + 早停 + 评估指标

v3: DeepFM返回raw logits, FocalLoss基于logits实现, 推理时手动sigmoid

核心设计:
1. FocalLoss(alpha=0.4, gamma=2.0) — 智能配对后正样本占比约61%, alpha调为0.4
2. Opacus PrivacyEngine — target_epsilon=1.0, max_grad_norm=1.0, 自动管理隐私预算
3. ModuleValidator.fix(model) — 替换LayerNorm为Opacus兼容的CompatibleRMSNorm
4. 评估指标: HR@k, NDCG@k, AUC-PR, SafetyViolationRate
5. 早停(patience=5) + gradient clipping + 每epoch验证集评估
6. 保存: model.pt + encoder.json + metadata.json
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader

from app.models.deepfm import DeepFM
from app.config import settings

logger = logging.getLogger(__name__)


class FocalLoss(nn.Module):
    """Focal Loss — 基于logits实现, 解决类别不平衡问题

    FocalLoss(p_t) = -alpha * (1 - p_t)^gamma * log(p_t)
    其中 p_t = sigmoid(logits) 对正类, 1-sigmoid(logits) 对负类

    Args:
        alpha: 正类权重 (0.4, 适配智能配对后约61%正样本占比)
        gamma: 难样本聚焦参数 (2.0, 标准值)
    """

    def __init__(self, alpha: float = 0.4, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """计算FocalLoss

        Args:
            logits: [batch, 1] raw logits (未经sigmoid)
            targets: [batch, 1] 目标标签 (0.0-1.0)
        Returns:
            loss: scalar
        """
        # BCE基础损失 (基于logits, 内部自动sigmoid)
        bce_loss = nn.functional.binary_cross_entropy_with_logits(
            logits, targets, reduction='none'
        )

        # 计算p_t: 对正类p_t=sigmoid(logits), 对负类p_t=1-sigmoid(logits)
        probs = torch.sigmoid(logits)
        p_t = targets * probs + (1 - targets) * (1 - probs)

        # alpha权重: 对正类alpha, 对负类(1-alpha)
        alpha_t = targets * self.alpha + (1 - targets) * (1 - self.alpha)

        # focal调制因子: (1 - p_t)^gamma
        focal_mod = (1 - p_t).pow(self.gamma)

        loss = alpha_t * focal_mod * bce_loss
        return loss.mean()


class DeepFMTrainer:
    """DeepFM训练器 — FocalLoss + DP-SGD + 早停"""

    def __init__(
        self,
        field_dims: List[int],
        embed_dim: int = settings.embed_dim,
        hidden_dims: List[int] = settings.hidden_dims,
        dropout: float = settings.dropout,
        embed_dropout: float = settings.embed_dropout,
        focal_alpha: float = settings.focal_loss_alpha,
        focal_gamma: float = settings.focal_loss_gamma,
        dp_enabled: bool = False,
        dp_target_epsilon: float = settings.dp_target_epsilon,
        dp_target_delta: float = settings.default_delta,
        dp_max_grad_norm: float = settings.dp_max_grad_norm,
    ):
        self.field_dims = field_dims
        self.embed_dim = embed_dim
        self.hidden_dims = hidden_dims
        self.dp_enabled = dp_enabled
        self.dp_target_epsilon = dp_target_epsilon
        self.dp_target_delta = dp_target_delta
        self.dp_max_grad_norm = dp_max_grad_norm

        # DP模式下使用零dropout，非DP模式使用正常dropout
        actual_dropout = settings.dp_dropout if dp_enabled else dropout
        actual_embed_dropout = settings.dp_embed_dropout if dp_enabled else embed_dropout

        # 初始化模型
        self.model = DeepFM(
            field_dims=field_dims,
            embed_dim=embed_dim,
            hidden_dims=hidden_dims,
            num_continuous=4,  # age_raw, bmi_raw, gfr_raw, liver_score_raw
            dropout=actual_dropout,
            embed_dropout=actual_embed_dropout,
        )

        # 损失函数
        self.criterion = FocalLoss(alpha=focal_alpha, gamma=focal_gamma)

        # Opacus PrivacyEngine (仅在dp_enabled时使用)
        self.privacy_engine = None
        self.accountant = None

        # 训练状态
        self.best_val_loss = float('inf')
        self.best_epoch = 0
        self.patience_counter = 0
        self.train_history: List[Dict[str, float]] = []

        # 设备
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)

    def setup_dp(self, train_loader: DataLoader) -> DataLoader:
        """配置Opacus DP-SGD

        Opacus PrivacyEngine设置target_epsilon, 自动管理隐私预算
        ModuleValidator.fix()替换LayerNorm为CompatibleRMSNorm

        注意: Opacus不支持手动epsilon递减, target_epsilon是训练结束时的累计隐私预算上限
        """
        try:
            from opacus import PrivacyEngine
            from opacus.validators import ModuleValidator

            # 替换不兼容模块 (LayerNorm → CompatibleRMSNorm)
            errors = ModuleValidator.validate(self.model)
            if errors:
                logger.info(f"Fixing {len(errors)} Opacus-incompatible modules: {errors}")
                self.model = ModuleValidator.fix(self.model)
                self.model.to(self.device)

            privacy_engine = PrivacyEngine()
            self.model, optimizer, train_loader = privacy_engine.make_private_with_epsilon(
                module=self.model,
                data_loader=train_loader,
                optimizer=self.optimizer,
                epochs=self.epochs,
                target_epsilon=self.dp_target_epsilon,
                target_delta=self.dp_target_delta,
                max_grad_norm=self.dp_max_grad_norm,
            )
            self.optimizer = optimizer
            self.privacy_engine = privacy_engine

            logger.info(
                f"DP-SGD configured: target_epsilon={self.dp_target_epsilon}, "
                f"max_grad_norm={self.dp_max_grad_norm}"
            )
            return train_loader

        except ImportError:
            logger.warning("Opacus not installed, DP-SGD disabled")
            self.dp_enabled = False
            return train_loader
        except Exception as e:
            logger.error(f"Failed to configure DP-SGD: {e}")
            self.dp_enabled = False
            return train_loader

    def train(
        self,
        train_dataset,
        val_dataset,
        epochs: int = settings.default_epochs,
        learning_rate: float = settings.default_learning_rate,
        batch_size: int = settings.default_batch_size,
        patience: int = settings.early_stopping_patience,
        weight_decay: float = settings.weight_decay,
        save_dir: str = settings.saved_models_dir,
    ) -> Dict[str, Any]:
        """训练循环

        Args:
            train_dataset: DrugRecommendationDataset
            val_dataset: DrugRecommendationDataset
            epochs: 训练轮数
            learning_rate: 学习率
            batch_size: 批次大小
            patience: 早停耐心值
            weight_decay: 权重衰减
            save_dir: 保存目录
        Returns:
            训练结果字典 (含 metadata, history, best_epoch等)
        """
        self.epochs = epochs

        # DataLoader
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True, drop_last=False
        )
        val_loader = DataLoader(
            val_dataset, batch_size=batch_size, shuffle=False, drop_last=False
        )

        # Optimizer
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=learning_rate, weight_decay=weight_decay
        )

        # DP-SGD配置
        if self.dp_enabled:
            train_loader = self.setup_dp(train_loader)

        # 训练循环
        logger.info(
            f"Training started: {epochs} epochs, lr={learning_rate}, "
            f"batch_size={batch_size}, dp={self.dp_enabled}"
        )

        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        for epoch in range(1, epochs + 1):
            # Train
            train_loss, train_metrics = self._train_epoch(train_loader, epoch)

            # Validate
            val_loss, val_metrics = self._eval_epoch(val_loader, epoch)

            # 记录历史
            history_entry = {
                'epoch': epoch,
                'train_loss': train_loss,
                'val_loss': val_loss,
                **train_metrics,
                **val_metrics,
            }
            self.train_history.append(history_entry)

            # DP隐私报告
            if self.dp_enabled and self.privacy_engine:
                epsilon_spent = self.privacy_engine.get_epsilon(
                    delta=settings.default_delta
                )
                history_entry['dp_epsilon_spent'] = epsilon_spent
                logger.info(
                    f"Epoch {epoch}: DP epsilon spent = {epsilon_spent:.4f}"
                )

            # 早停检查
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.best_epoch = epoch
                self.patience_counter = 0
                # 保存最佳模型
                self._save_model(save_path / "best_model.pt")
            else:
                self.patience_counter += 1
                if self.patience_counter >= patience:
                    logger.info(
                        f"Early stopping at epoch {epoch}, best epoch={self.best_epoch}, "
                        f"best val_loss={self.best_val_loss:.4f}"
                    )
                    break

            logger.info(
                f"Epoch {epoch}/{epochs}: train_loss={train_loss:.4f}, "
                f"val_loss={val_loss:.4f}, "
                f"train_auc_pr={train_metrics.get('auc_pr', 0):.4f}, "
                f"val_auc_pr={val_metrics.get('auc_pr', 0):.4f}"
            )

        # 保存最终模型和metadata
        self._save_model(save_path / "final_model.pt")
        metadata = self._build_metadata(train_dataset, val_dataset)

        with open(save_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Training completed: best_epoch={self.best_epoch}, "
            f"best_val_loss={self.best_val_loss:.4f}"
        )

        return metadata

    def _train_epoch(self, loader: DataLoader, epoch: int) -> Tuple[float, Dict]:
        """单epoch训练"""
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_labels = []

        for batch in loader:
            field_indices = batch['field_indices'].to(self.device)
            continuous_features = batch['continuous_features'].to(self.device)
            labels = batch['label'].to(self.device)

            self.optimizer.zero_grad()
            logits, _ = self.model(field_indices, continuous_features)
            loss = self.criterion(logits, labels)
            loss.backward()

            # Gradient clipping (非DP-SGD时手动clip, DP-SGD时Opacus自动clip)
            if not self.dp_enabled:
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.dp_max_grad_norm
                )

            self.optimizer.step()

            total_loss += loss.item() * len(labels)
            probs = torch.sigmoid(logits).detach().cpu().numpy().flatten()
            all_preds.extend(probs)
            all_labels.extend(labels.detach().cpu().numpy().flatten())

        avg_loss = total_loss / len(all_labels)
        metrics = self._compute_metrics(np.array(all_preds), np.array(all_labels))
        return avg_loss, metrics

    def _eval_epoch(self, loader: DataLoader, epoch: int) -> Tuple[float, Dict]:
        """单epoch评估"""
        self.model.eval()
        total_loss = 0.0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for batch in loader:
                field_indices = batch['field_indices'].to(self.device)
                continuous_features = batch['continuous_features'].to(self.device)
                labels = batch['label'].to(self.device)

                logits, _ = self.model(field_indices, continuous_features)
                loss = self.criterion(logits, labels)

                total_loss += loss.item() * len(labels)
                probs = torch.sigmoid(logits).detach().cpu().numpy().flatten()
                all_preds.extend(probs)
                all_labels.extend(labels.detach().cpu().numpy().flatten())

        avg_loss = total_loss / len(all_labels)
        metrics = self._compute_metrics(np.array(all_preds), np.array(all_labels))
        return avg_loss, metrics

    def _compute_metrics(
        self, preds: np.ndarray, labels: np.ndarray
    ) -> Dict[str, float]:
        """计算评估指标

        指标:
        - AUC-PR: 对不平衡数据更有意义的指标
        - HR@k: 前k推荐中含正样本(label>=0.7)的比例
        - SafetyViolationRate: 前k推荐中含硬排除样本(label=0.0)的比例
        - MeanPredPositive: 正样本的平均预测概率
        - MeanPredNegative: 负样本(label<=0.05)的平均预测概率
        """
        metrics = {}

        # AUC-PR (对不平衡数据更有意义)
        try:
            from sklearn.metrics import average_precision_score
            # 二值化: label >= 0.5 为正
            binary_labels = (labels >= 0.5).astype(int)
            if binary_labels.sum() > 0 and (1 - binary_labels).sum() > 0:
                metrics['auc_pr'] = average_precision_score(binary_labels, preds)
            else:
                metrics['auc_pr'] = 0.0
        except ImportError:
            # fallback: 简易AUC-PR计算
            metrics['auc_pr'] = self._simple_auc_pr(preds, labels)

        # HR@4, HR@10
        for k in [4, 10]:
            top_k_indices = np.argsort(preds)[::-1][:k]
            top_k_labels = labels[top_k_indices]
            metrics[f'hr@{k}'] = float(np.mean(top_k_labels >= 0.7))

        # SafetyViolationRate: 前k推荐中含label=0.0的比例
        top_4_indices = np.argsort(preds)[::-1][:4]
        top_4_labels = labels[top_4_indices]
        metrics['safety_violation_rate@4'] = float(np.mean(top_4_labels == 0.0))

        # 预测分布
        positive_mask = labels >= 0.7
        negative_mask = labels <= 0.05
        if positive_mask.any():
            metrics['mean_pred_positive'] = float(preds[positive_mask].mean())
        if negative_mask.any():
            metrics['mean_pred_negative'] = float(preds[negative_mask].mean())

        return metrics

    def _simple_auc_pr(self, preds: np.ndarray, labels: np.ndarray) -> float:
        """简易AUC-PR计算 (sklearn不可用时fallback)"""
        binary_labels = (labels >= 0.5).astype(int)
        if binary_labels.sum() == 0:
            return 0.0
        sorted_indices = np.argsort(preds)[::-1]
        precisions = []
        recalls = []
        tp = 0
        total_positives = binary_labels.sum()
        for i, idx in enumerate(sorted_indices):
            if binary_labels[idx] == 1:
                tp += 1
            precision = tp / (i + 1)
            recall = tp / total_positives
            precisions.append(precision)
            recalls.append(recall)
        if not precisions:
            return 0.0
        return float(np.mean(precisions))

    def _save_model(self, path: Path) -> None:
        """保存模型state_dict"""
        torch.save(self.model.state_dict(), path)
        logger.info(f"Model saved to {path}")

    def _build_metadata(self, train_dataset, val_dataset) -> Dict[str, Any]:
        """构建训练metadata"""
        metadata = {
            'best_epoch': self.best_epoch,
            'best_val_loss': self.best_val_loss,
            'field_dims': self.field_dims,
            'embed_dim': self.embed_dim,
            'hidden_dims': self.hidden_dims,
            'focal_alpha': settings.focal_loss_alpha,
            'focal_gamma': settings.focal_loss_gamma,
            'dp_enabled': self.dp_enabled,
            'dp_target_epsilon': self.dp_target_epsilon if self.dp_enabled else None,
            'dp_epsilon_spent': None,
            'num_train_samples': len(train_dataset),
            'num_val_samples': len(val_dataset),
            'train_history': self.train_history,
            'model_version': 'v3_logits',
            'description': 'DeepFM v3 (raw logits output, manual sigmoid at inference)',
        }

        # DP最终隐私预算
        if self.dp_enabled and self.privacy_engine:
            metadata['dp_epsilon_spent'] = self.privacy_engine.get_epsilon(
                delta=settings.default_delta
            )

        return metadata