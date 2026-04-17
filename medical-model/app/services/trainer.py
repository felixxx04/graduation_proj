"""
模型训练服务
支持差分隐私训练 (DP-SGD)

改进点：
- 参数校验与防御性编程
- 训练/验证集拆分
- 早停机制
- 正确的差分隐私 epsilon 预算计算
- 训练状态持久化与恢复
- 细粒度日志与指标记录
- 梯度异常检测
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import time
import json
import os
import numpy as np
from app.models.deepfm import DeepFM
from app.utils.privacy import laplace_noise, compute_epsilon_spent
from app.exceptions import TrainingError, TrainingParameterError, TrainingStateError

logger = logging.getLogger(__name__)


class DrugRecommendationDataset(Dataset):
    """药物推荐训练数据集"""

    def __init__(self, samples: List[Dict[str, Any]], feature_dim: int = 200):
        """
        初始化数据集

        Args:
            samples: 训练样本列表
            feature_dim: 特征维度

        Raises:
            TrainingParameterError: 样本格式无效
        """
        if not samples:
            raise TrainingParameterError("Samples list must not be empty")
        if feature_dim <= 0:
            raise TrainingParameterError(f"Invalid feature_dim: {feature_dim}")

        self.feature_dim = feature_dim
        self._validate_samples(samples)
        self.samples = samples

    def _validate_samples(self, samples: List[Dict[str, Any]]) -> None:
        """校验样本格式"""
        for i, sample in enumerate(samples):
            if not isinstance(sample, dict):
                raise TrainingParameterError(f"Sample {i} must be a dict, got {type(sample)}")

            label = sample.get('label')
            if label is not None:
                try:
                    float(label)
                except (TypeError, ValueError):
                    raise TrainingParameterError(
                        f"Sample {i} has invalid label: {label}"
                    )

            features = sample.get('features')
            if features is not None:
                if isinstance(features, (list, np.ndarray)):
                    if len(features) != self.feature_dim:
                        raise TrainingParameterError(
                            f"Sample {i} feature dim mismatch: "
                            f"expected {self.feature_dim}, got {len(features)}"
                        )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]
        features = sample.get('features', np.zeros(self.feature_dim, dtype=np.float32))
        label = sample.get('label', 0.0)

        if not isinstance(features, torch.Tensor):
            features = torch.tensor(features, dtype=torch.float32)

        # 确保特征维度正确
        if features.shape[0] != self.feature_dim:
            padded = torch.zeros(self.feature_dim, dtype=torch.float32)
            length = min(features.shape[0], self.feature_dim)
            padded[:length] = features[:length]
            features = padded

        label_val = float(label)
        if not (0.0 <= label_val <= 1.0):
            logger.warning(f"Label {label_val} out of [0,1] range at index {idx}, clipping")
            label_val = max(0.0, min(1.0, label_val))

        return {
            'features': features,
            'label': torch.tensor(label_val, dtype=torch.float32)
        }


@dataclass
class TrainingConfig:
    """训练配置"""
    epochs: int = 10
    learning_rate: float = 0.01
    batch_size: int = 32
    max_grad_norm: float = 1.0
    val_split: float = 0.2
    early_stopping_patience: int = 5
    early_stopping_delta: float = 1e-4
    dp_enabled: bool = False
    dp_epsilon: float = 1.0
    dp_delta: float = 1e-5
    dp_sensitivity: float = 1.0

    def validate(self) -> None:
        """校验训练参数"""
        if self.epochs <= 0 or self.epochs > 1000:
            raise TrainingParameterError(f"epochs must be in [1, 1000], got {self.epochs}")
        if self.learning_rate <= 0 or self.learning_rate > 1.0:
            raise TrainingParameterError(f"learning_rate must be in (0, 1.0], got {self.learning_rate}")
        if self.batch_size <= 0 or self.batch_size > 1024:
            raise TrainingParameterError(f"batch_size must be in [1, 1024], got {self.batch_size}")
        if self.max_grad_norm <= 0:
            raise TrainingParameterError(f"max_grad_norm must be > 0, got {self.max_grad_norm}")
        if not (0.0 <= self.val_split < 0.5):
            raise TrainingParameterError(f"val_split must be in [0, 0.5), got {self.val_split}")
        if self.early_stopping_patience < 0:
            raise TrainingParameterError(f"early_stopping_patience must be >= 0, got {self.early_stopping_patience}")
        if self.dp_enabled:
            if self.dp_epsilon <= 0:
                raise TrainingParameterError(f"dp_epsilon must be > 0, got {self.dp_epsilon}")
            if self.dp_delta <= 0 or self.dp_delta >= 1:
                raise TrainingParameterError(f"dp_delta must be in (0, 1), got {self.dp_delta}")
            if self.dp_sensitivity <= 0:
                raise TrainingParameterError(f"dp_sensitivity must be > 0, got {self.dp_sensitivity}")


class EarlyStoppingTracker:
    """早停追踪器"""

    def __init__(self, patience: int = 5, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float('inf')
        self.counter = 0
        self.should_stop = False

    def step(self, val_loss: float) -> bool:
        """
        检查是否应早停

        Returns:
            True 表示应该停止训练
        """
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
                logger.info(
                    f"Early stopping triggered: no improvement for {self.patience} epochs "
                    f"(best_loss={self.best_loss:.4f})"
                )
        return self.should_stop


class TrainingState:
    """训练状态管理，支持断点续训"""

    def __init__(self):
        self.epoch = 0
        self.history: Dict[str, List[float]] = {'loss': [], 'accuracy': [], 'val_loss': [], 'val_accuracy': []}
        self.best_val_loss = float('inf')
        self.total_epsilon_spent = 0.0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'epoch': self.epoch,
            'history': self.history,
            'best_val_loss': self.best_val_loss,
            'total_epsilon_spent': self.total_epsilon_spent,
            'start_time': self.start_time,
            'end_time': self.end_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingState':
        state = cls()
        state.epoch = data.get('epoch', 0)
        state.history = data.get('history', {'loss': [], 'accuracy': [], 'val_loss': [], 'val_accuracy': []})
        state.best_val_loss = data.get('best_val_loss', float('inf'))
        state.total_epsilon_spent = data.get('total_epsilon_spent', 0.0)
        state.start_time = data.get('start_time')
        state.end_time = data.get('end_time')
        return state

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> Optional['TrainingState']:
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load training state from {filepath}: {e}")
            return None


class ModelTrainer:
    """模型训练器，支持差分隐私与早停"""

    def __init__(self, model: DeepFM, device: torch.device):
        self.model = model
        self.device = device
        self.criterion = nn.BCELoss()

    def train(
        self,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        config: Optional[TrainingConfig] = None,
        dp_config: Optional[Dict[str, Any]] = None,
        # Legacy 参数兼容
        epochs: int = 10,
        learning_rate: float = 0.01,
        batch_size: int = 32,
        max_grad_norm: float = 1.0,
    ) -> Dict[str, Any]:
        """
        训练模型

        Args:
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器
            config: 训练配置（推荐）
            dp_config: 差分隐私配置（兼容旧接口）
            epochs, learning_rate, batch_size, max_grad_norm: 兼容旧接口

        Returns:
            训练结果字典
        """
        # 合并新旧配置
        if config is None:
            config = TrainingConfig(
                epochs=epochs,
                learning_rate=learning_rate,
                batch_size=batch_size,
                max_grad_norm=max_grad_norm,
            )
            # 从旧 dp_config 迁移
            if dp_config and dp_config.get('enabled', False):
                config.dp_enabled = True
                config.dp_epsilon = dp_config.get('epsilon', 1.0)
                config.dp_delta = dp_config.get('delta', 1e-5)
                config.dp_sensitivity = dp_config.get('sensitivity', 1.0)

        config.validate()

        # 初始化训练状态
        state = TrainingState()
        state.start_time = time.time()

        optimizer = optim.Adam(self.model.parameters(), lr=config.learning_rate)
        early_stopping = EarlyStoppingTracker(
            patience=config.early_stopping_patience,
            min_delta=config.early_stopping_delta,
        ) if config.early_stopping_patience > 0 else None

        dataset_size = len(train_loader.dataset)
        logger.info(
            f"Starting training: epochs={config.epochs}, lr={config.learning_rate}, "
            f"dp_enabled={config.dp_enabled}, dataset_size={dataset_size}"
        )

        for epoch in range(config.epochs):
            state.epoch = epoch + 1
            train_loss, train_acc = self._train_epoch(
                train_loader, optimizer, config
            )
            state.history['loss'].append(train_loss)
            state.history['accuracy'].append(train_acc)

            # 验证
            val_loss, val_acc = 0.0, 0.0
            if val_loader:
                val_metrics = self._evaluate_epoch(val_loader)
                val_loss, val_acc = val_metrics['loss'], val_metrics['accuracy']
                state.history['val_loss'].append(val_loss)
                state.history['val_accuracy'].append(val_acc)

            # DP 预算累计
            if config.dp_enabled:
                step_epsilon = compute_epsilon_spent(
                    steps=(epoch + 1) * len(train_loader),
                    batch_size=config.batch_size,
                    dataset_size=dataset_size,
                    noise_multiplier=config.dp_epsilon,
                    delta=config.dp_delta,
                )
                state.total_epsilon_spent = step_epsilon

            log_msg = (
                f"Epoch {epoch + 1}/{config.epochs} - "
                f"Loss: {train_loss:.4f}, Acc: {train_acc:.4f}"
            )
            if val_loader:
                log_msg += f", Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}"
            if config.dp_enabled:
                log_msg += f", Epsilon spent: {state.total_epsilon_spent:.4f}"
            logger.info(log_msg)

            # 早停检查
            if early_stopping and val_loader and early_stopping.step(val_loss):
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break

        state.end_time = time.time()
        duration = state.end_time - state.start_time

        return {
            'epochs': state.epoch,
            'total_epochs_requested': config.epochs,
            'final_loss': state.history['loss'][-1] if state.history['loss'] else 0,
            'final_accuracy': state.history['accuracy'][-1] if state.history['accuracy'] else 0,
            'final_val_loss': state.history['val_loss'][-1] if state.history['val_loss'] else None,
            'final_val_accuracy': state.history['val_accuracy'][-1] if state.history['val_accuracy'] else None,
            'history': state.history,
            'dp_enabled': config.dp_enabled,
            'epsilon_spent': state.total_epsilon_spent if config.dp_enabled else 0,
            'duration_seconds': round(duration, 2),
            'early_stopped': early_stopping.should_stop if early_stopping else False,
        }

    def _train_epoch(
        self,
        train_loader: DataLoader,
        optimizer: optim.Optimizer,
        config: TrainingConfig,
    ) -> tuple:
        """执行一个训练 epoch"""
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        nan_batches = 0

        for batch_idx, batch in enumerate(train_loader):
            features = batch['features'].to(self.device)
            labels = batch['label'].to(self.device)

            optimizer.zero_grad()
            outputs, _ = self.model(features)
            outputs = outputs.squeeze()

            if outputs.dim() == 0:
                outputs = outputs.unsqueeze(0)

            # 检测输出范围
            if outputs.min() < 0 or outputs.max() > 1:
                outputs = outputs.clamp(1e-7, 1 - 1e-7)

            loss = self.criterion(outputs, labels)

            # NaN 检测
            if torch.isnan(loss) or torch.isinf(loss):
                nan_batches += 1
                logger.warning(f"NaN/Inf loss at batch {batch_idx}, skipping")
                continue

            loss.backward()

            # 梯度裁剪
            grad_norm = torch.nn.utils.clip_grad_norm_(
                self.model.parameters(), config.max_grad_norm
            )

            # 梯度异常检测
            if grad_norm > 100.0:
                logger.warning(f"Large gradient norm detected: {grad_norm:.2f}")

            # 差分隐私：梯度噪声注入
            if config.dp_enabled:
                with torch.no_grad():
                    for param in self.model.parameters():
                        if param.grad is not None:
                            noise = torch.tensor(
                                laplace_noise(param.grad.shape, config.dp_epsilon, config.dp_sensitivity),
                                dtype=param.grad.dtype,
                                device=self.device
                            )
                            param.grad.add_(noise)

            optimizer.step()

            total_loss += loss.item()
            predictions = (outputs > 0.5).float()
            correct += (predictions == labels).sum().item()
            total += labels.size(0)

        if nan_batches > 0:
            logger.warning(f"Skipped {nan_batches} batches due to NaN/Inf loss")

        avg_loss = total_loss / max(len(train_loader) - nan_batches, 1)
        accuracy = correct / total if total > 0 else 0
        return avg_loss, accuracy

    def _evaluate_epoch(self, val_loader: DataLoader) -> Dict[str, float]:
        """评估一个 epoch"""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch in val_loader:
                features = batch['features'].to(self.device)
                labels = batch['label'].to(self.device)

                outputs, _ = self.model(features)
                outputs = outputs.squeeze()

                if outputs.dim() == 0:
                    outputs = outputs.unsqueeze(0)

                outputs = outputs.clamp(1e-7, 1 - 1e-7)
                loss = self.criterion(outputs, labels)
                total_loss += loss.item()

                predictions = (outputs > 0.5).float()
                correct += (predictions == labels).sum().item()
                total += labels.size(0)

        return {
            'loss': total_loss / len(val_loader) if val_loader else 0,
            'accuracy': correct / total if total > 0 else 0
        }

    def evaluate(self, test_loader: DataLoader) -> Dict[str, float]:
        """评估模型（公共接口）"""
        return self._evaluate_epoch(test_loader)


def create_data_loaders(
    samples: List[Dict[str, Any]],
    feature_dim: int = 200,
    batch_size: int = 32,
    val_split: float = 0.2,
) -> tuple:
    """
    创建训练/验证数据加载器

    Args:
        samples: 训练样本
        feature_dim: 特征维度
        batch_size: 批次大小
        val_split: 验证集比例

    Returns:
        (train_loader, val_loader)
    """
    dataset = DrugRecommendationDataset(samples, feature_dim=feature_dim)

    if val_split > 0 and len(dataset) > 10:
        val_size = max(1, int(len(dataset) * val_split))
        train_size = len(dataset) - val_size
        train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    else:
        train_dataset = dataset
        val_dataset = None

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=0
    )
    val_loader = None
    if val_dataset:
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    return train_loader, val_loader


def generate_synthetic_training_data(
    num_samples: int = 1000,
    feature_dim: int = 200,
    drugs_count: int = 10
) -> List[Dict[str, Any]]:
    """
    生成合成训练数据用于演示

    注意：仅用于无真实数据时的演示，生产环境应使用真实数据
    """
    if num_samples <= 0:
        raise TrainingParameterError(f"num_samples must be > 0, got {num_samples}")

    np.random.seed(42)
    samples = []

    # 固定随机权重，确保可复现
    weight = np.random.randn(10).astype(np.float32)

    for i in range(num_samples):
        features = np.random.randn(feature_dim).astype(np.float32)
        score = np.dot(features[:10], weight) + np.random.randn() * 0.1
        label = 1.0 if score > 0 else 0.0

        samples.append({
            'patient_id': i % 100,
            'drug_id': i % drugs_count,
            'features': features,
            'label': label
        })

    logger.info(f"Generated {len(samples)} synthetic training samples")
    return samples
