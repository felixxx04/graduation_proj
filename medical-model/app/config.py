from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """模型服务配置，支持环境变量覆盖"""

    # 应用配置
    app_name: str = "Medical Recommendation Model Service"
    debug: bool = False

    # 模型配置
    embed_dim: int = 16
    hidden_dims: List[int] = [128, 64, 32]
    dropout: float = 0.3
    embed_dropout: float = 0.1

    # 差分隐私默认参数
    default_epsilon: float = 0.1
    default_delta: float = 1e-5
    default_sensitivity: float = 1.0

    # 训练默认参数
    default_epochs: int = 10
    default_learning_rate: float = 0.001
    default_batch_size: int = 128
    default_lambda_contra: float = 2.0
    early_stopping_patience: int = 5
    contra_oversample: int = 2
    warmup_epochs: int = 5
    weight_decay: float = 1e-5

    # DP-SGD 参数
    dp_max_grad_norm: float = 1.0

    # 路径
    data_dir: str = "data"
    saved_models_dir: str = "saved_models"
    model_versions_to_keep: int = 3

    # 安全阈值
    contra_leak_threshold: float = 0.05

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()