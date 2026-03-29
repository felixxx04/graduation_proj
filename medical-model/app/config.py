from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Medical Recommendation Model Service"
    model_path: str = "saved_models/deepfm.pt"
    default_epsilon: float = 0.1
    default_delta: float = 1e-5
    default_sensitivity: float = 1.0
    
    class Config:
        env_file = ".env"

settings = Settings()
