from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """模型服务配置，支持环境变量覆盖

    v3: embed_dim=16(优化DP-SGD下区分度), DP模式下自动关闭dropout,
    dp_max_grad_norm=1.0, batch_size=256(DP时Opacus建议较大batch)
    """

    # 应用配置
    app_name: str = "Medical Recommendation Model Service"
    debug: bool = False

    # 模型配置 (v3: embed_dim从8提升到16, 改善DP-SGD下的separation)
    embed_dim: int = 16
    hidden_dims: List[int] = [64, 32]
    dropout: float = 0.1       # 非DP模式使用
    embed_dropout: float = 0.1  # 非DP模式使用
    dp_dropout: float = 0.0     # DP模式使用 (关闭dropout, 让模型靠梯度信号学习)
    dp_embed_dropout: float = 0.0  # DP模式使用

    # 差分隐私默认参数
    default_epsilon: float = 1.0
    default_delta: float = 1e-5
    default_sensitivity: float = 1.0

    # 训练默认参数
    default_epochs: int = 10
    default_learning_rate: float = 0.001
    default_batch_size: int = 256
    focal_loss_alpha: float = 0.4  # 适配智能配对后约61%正样本占比
    focal_loss_gamma: float = 2.0
    early_stopping_patience: int = 5
    weight_decay: float = 5e-4

    # DP-SGD 参数 (v3: dp_max_grad_norm=1.0, DP训练时使用较大batch)
    dp_max_grad_norm: float = 1.0
    dp_target_epsilon: float = 1.0
    dp_batch_size: int = 256  # DP训练专用batch_size

    # 路径
    data_dir: str = "data"
    saved_models_dir: str = "saved_models"
    audit_log_dir: str = "audit_logs"
    model_versions_to_keep: int = 3

    # 安全阈值
    contra_leak_threshold: float = 0.05

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()