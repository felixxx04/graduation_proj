"""
模型训练服务
支持差分隐私训练 (DP-SGD)
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from typing import Dict, Any, Optional, List
import logging
import numpy as np
from app.models.deepfm import DeepFM
from app.utils.privacy import laplace_noise

logger = logging.getLogger(__name__)


class DrugRecommendationDataset(Dataset):
    """药物推荐训练数据集"""

    def __init__(self, samples: List[Dict[str, Any]], feature_dim: int = 200):
        self.samples = samples
        self.feature_dim = feature_dim

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        features = sample.get('features', np.zeros(self.feature_dim, dtype=np.float32))
        label = sample.get('label', 0.0)

        if not isinstance(features, torch.Tensor):
            features = torch.tensor(features, dtype=torch.float32)

        return {
            'features': features,
            'label': torch.tensor(label, dtype=torch.float32)
        }


class ModelTrainer:
    """模型训练器，支持差分隐私"""

    def __init__(self, model: DeepFM, device: torch.device):
        self.model = model
        self.device = device
        self.criterion = nn.BCELoss()

    def train(
        self,
        train_loader: DataLoader,
        epochs: int = 10,
        learning_rate: float = 0.01,
        dp_config: Optional[Dict[str, Any]] = None,
        batch_size: int = 32,
        max_grad_norm: float = 1.0
    ) -> Dict[str, Any]:
        """
        训练模型

        Args:
            train_loader: 训练数据加载器
            epochs: 训练轮数
            learning_rate: 学习率
            dp_config: 差分隐私配置
            batch_size: 批次大小
            max_grad_norm: 梯度裁剪阈值

        Returns:
            训练结果字典
        """
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)

        history = {'loss': [], 'accuracy': []}
        dp_enabled = dp_config and dp_config.get('enabled', False)
        epsilon = dp_config.get('epsilon', 1.0) if dp_config else 1.0
        sensitivity = dp_config.get('sensitivity', 1.0) if dp_config else 1.0

        logger.info(f"Starting training: epochs={epochs}, lr={learning_rate}, dp_enabled={dp_enabled}")

        for epoch in range(epochs):
            self.model.train()
            total_loss = 0.0
            correct = 0
            total = 0

            for batch_idx, batch in enumerate(train_loader):
                features = batch['features'].to(self.device)
                labels = batch['label'].to(self.device)

                optimizer.zero_grad()

                # 前向传播
                outputs, _ = self.model(features)
                outputs = outputs.squeeze()

                # 确保输出和标签形状匹配
                if outputs.dim() == 0:
                    outputs = outputs.unsqueeze(0)

                loss = self.criterion(outputs, labels)

                # 反向传播
                loss.backward()

                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_grad_norm)

                # 差分隐私：在梯度上添加噪声
                if dp_enabled:
                    with torch.no_grad():
                        for param in self.model.parameters():
                            if param.grad is not None:
                                noise = torch.tensor(
                                    laplace_noise(param.grad.shape, epsilon, sensitivity),
                                    dtype=param.grad.dtype,
                                    device=self.device
                                )
                                param.grad.add_(noise)

                optimizer.step()

                total_loss += loss.item()
                predictions = (outputs > 0.5).float()
                correct += (predictions == labels).sum().item()
                total += labels.size(0)

            avg_loss = total_loss / len(train_loader)
            accuracy = correct / total if total > 0 else 0
            history['loss'].append(avg_loss)
            history['accuracy'].append(accuracy)

            logger.info(f"Epoch {epoch + 1}/{epochs} - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}")

        return {
            'epochs': epochs,
            'final_loss': history['loss'][-1] if history['loss'] else 0,
            'final_accuracy': history['accuracy'][-1] if history['accuracy'] else 0,
            'history': history,
            'dp_enabled': dp_enabled,
            'epsilon_used': epsilon * epochs if dp_enabled else 0
        }

    def evaluate(self, test_loader: DataLoader) -> Dict[str, float]:
        """评估模型"""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for batch in test_loader:
                features = batch['features'].to(self.device)
                labels = batch['label'].to(self.device)

                outputs, _ = self.model(features)
                outputs = outputs.squeeze()

                if outputs.dim() == 0:
                    outputs = outputs.unsqueeze(0)

                loss = self.criterion(outputs, labels)
                total_loss += loss.item()

                predictions = (outputs > 0.5).float()
                correct += (predictions == labels).sum().item()
                total += labels.size(0)

        return {
            'loss': total_loss / len(test_loader) if test_loader else 0,
            'accuracy': correct / total if total > 0 else 0
        }


def generate_synthetic_training_data(
    num_samples: int = 1000,
    feature_dim: int = 200,
    drugs_count: int = 10
) -> List[Dict[str, Any]]:
    """
    生成合成训练数据用于演示
    在没有真实数据时使用
    """
    np.random.seed(42)
    samples = []

    for i in range(num_samples):
        # 生成随机特征
        features = np.random.randn(feature_dim).astype(np.float32)

        # 生成标签（基于特征的简单规则）
        # 这里使用一个简单的线性组合 + 随机噪声
        score = np.dot(features[:10], np.random.randn(10)) + np.random.randn() * 0.1
        label = 1.0 if score > 0 else 0.0

        samples.append({
            'patient_id': i % 100,
            'drug_id': i % drugs_count,
            'features': features,
            'label': label
        })

    logger.info(f"Generated {len(samples)} synthetic training samples")
    return samples
