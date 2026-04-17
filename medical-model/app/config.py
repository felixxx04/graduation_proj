from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """模型服务配置，支持环境变量覆盖"""

    # 应用配置
    app_name: str = "Medical Recommendation Model Service"
    debug: bool = False

    # 模型配置
    model_path: str = "saved_models/deepfm.pt"
    feature_dim: int = 200

    # 差分隐私默认参数
    default_epsilon: float = 0.1
    default_delta: float = 1e-5
    default_sensitivity: float = 1.0

    # OpenFDA 数据源配置
    openfda_base_url: str = "https://api.fda.gov/drug"
    openfda_api_key: Optional[str] = None
    openfda_rate_limit_delay: float = 0.5
    openfda_connect_timeout: int = 10
    openfda_read_timeout: int = 30
    openfda_max_retries: int = 3

    # 数据库配置（用于训练数据生成脚本）
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "medical_recommendation"
    db_charset: str = "utf8mb4"

    # 训练默认参数
    default_epochs: int = 10
    default_learning_rate: float = 0.01
    default_batch_size: int = 32
    default_max_grad_norm: float = 1.0
    early_stopping_patience: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
