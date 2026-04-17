from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import json
import os
import time
import logging
import torch
from app.config import settings
from app.services.predictor import predictor
from app.exceptions import (
    ModelServiceError,
    DataNotFoundError,
    DataValidationError,
    ModelNotLoadedError,
    PredictionError,
    TrainingParameterError,
    TrainingError,
    PrivacyConfigError,
    PrivacyBudgetExceededError,
    DataSourceError,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0"
)

# ── 全局异常处理：将 ModelServiceError 子类自动转为 HTTP 响应 ──

_EXCEPTION_STATUS_MAP: Dict[type, int] = {
    DataNotFoundError: 404,
    DataValidationError: 422,
    ModelNotLoadedError: 503,
    PredictionError: 500,
    TrainingParameterError: 400,
    TrainingError: 500,
    PrivacyConfigError: 400,
    PrivacyBudgetExceededError: 429,
    DataSourceError: 502,
}


@app.exception_handler(ModelServiceError)
async def model_service_error_handler(request: Request, exc: ModelServiceError) -> JSONResponse:
    """将自定义异常层次统一转换为结构化 JSON 响应"""
    status_code = _EXCEPTION_STATUS_MAP.get(type(exc), 500)
    logger.error(
        f"ModelServiceError [{exc.error_code}]: {exc.message}",
        extra={"details": exc.details},
        exc_info=True,
    )
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
    )


# 文件路径
DRUGS_DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'drugs_openfda.json')
TRAINED_MODEL_FILE = os.path.join(os.path.dirname(__file__), '..', 'saved_models', 'deepfm_trained.pt')


class DPConfig(BaseModel):
    enabled: bool = True
    epsilon: float = 0.1
    delta: float = 1e-5
    sensitivity: float = 1.0
    noiseMechanism: str = "laplace"
    applicationStage: str = "model"

    @field_validator('epsilon')
    @classmethod
    def validate_epsilon(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('epsilon must be > 0')
        return v

    @field_validator('delta')
    @classmethod
    def validate_delta(cls, v: float) -> float:
        if v <= 0 or v >= 1:
            raise ValueError('delta must be in (0, 1)')
        return v

    @field_validator('noiseMechanism')
    @classmethod
    def validate_mechanism(cls, v: str) -> str:
        if v not in ('laplace', 'gaussian'):
            raise ValueError('noiseMechanism must be "laplace" or "gaussian"')
        return v


class PredictRequest(BaseModel):
    patientId: Optional[int] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    diseases: Optional[str] = None
    symptoms: Optional[str] = None
    allergies: Optional[str] = None
    currentMedications: Optional[str] = None
    dpEnabled: bool = True
    topK: int = 4
    dpConfig: Optional[DPConfig] = None

    @field_validator('topK')
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError('topK must be in [1, 20]')
        return v

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 150):
            raise ValueError('age must be in [0, 150]')
        return v


class TrainRequest(BaseModel):
    epochs: int = 10
    learningRate: float = 0.01
    dpEnabled: bool = True
    epsilon: float = 1.0
    batchSize: int = 32

    @field_validator('epochs')
    @classmethod
    def validate_epochs(cls, v: int) -> int:
        if v < 1 or v > 1000:
            raise ValueError('epochs must be in [1, 1000]')
        return v

    @field_validator('learningRate')
    @classmethod
    def validate_lr(cls, v: float) -> float:
        if v <= 0 or v > 1.0:
            raise ValueError('learningRate must be in (0, 1.0]')
        return v

    @field_validator('epsilon')
    @classmethod
    def validate_epsilon(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('epsilon must be > 0')
        return v

    @field_validator('batchSize')
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v < 1 or v > 1024:
            raise ValueError('batchSize must be in [1, 1024]')
        return v


@app.on_event("startup")
async def startup():
    logger.info("Model service starting up...")

    # 加载药物数据
    if os.path.exists(DRUGS_DATA_FILE):
        try:
            with open(DRUGS_DATA_FILE, 'r', encoding='utf-8') as f:
                drugs_data = json.load(f)
            predictor.set_drugs_data(drugs_data)
            logger.info(f"Loaded {len(drugs_data)} drugs from {DRUGS_DATA_FILE}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in drugs data file: {e}")
        except Exception as e:
            logger.error(f"Failed to load drugs data: {e}", exc_info=True)
    else:
        logger.warning(f"Drugs data file not found: {DRUGS_DATA_FILE}")

    # 加载已训练的模型
    if os.path.exists(TRAINED_MODEL_FILE):
        try:
            predictor.load_model(TRAINED_MODEL_FILE, field_dims=[200])
            logger.info(f"Loaded trained model from {TRAINED_MODEL_FILE}")
        except Exception as e:
            logger.warning(f"Could not load trained model: {e}", exc_info=True)
    else:
        logger.info("No trained model found, will use mock predictions until training is done")


@app.get("/")
def root():
    return {"message": "Medical Recommendation Model Service", "status": "running"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "modelLoaded": predictor.model is not None,
        "drugsCount": len(predictor.drugs_data),
    }


@app.get("/model/status")
def status():
    return {
        "modelLoaded": predictor.model is not None,
        "device": str(predictor.device),
        "drugsCount": len(predictor.drugs_data)
    }


@app.post("/model/predict")
def predict(request: PredictRequest):
    patient_data = {
        'id': request.patientId,
        'age': request.age,
        'gender': request.gender,
        'chronic_diseases': request.diseases.split('，') if request.diseases else [],
        'symptoms': request.symptoms,
        'allergies': request.allergies.split('，') if request.allergies else [],
        'current_medications': request.currentMedications.split('，') if request.currentMedications else []
    }

    dp_config = None
    if request.dpEnabled:
        if request.dpConfig:
            dp_config = request.dpConfig.dict()
        else:
            dp_config = {
                'enabled': True,
                'epsilon': settings.default_epsilon,
                'delta': settings.default_delta,
                'sensitivity': settings.default_sensitivity,
                'noiseMechanism': 'laplace'
            }

    # ModelServiceError 子类由全局异常处理器统一处理
    # DataNotFoundError → 404, PrivacyConfigError → 400, PredictionError → 500
    return predictor.predict(patient_data, request.topK, dp_config)


@app.post("/model/train")
def train(request: TrainRequest):
    """训练模型"""
    from app.services.trainer import (
        ModelTrainer, TrainingConfig,
        create_data_loaders, generate_synthetic_training_data
    )

    # 准备训练数据
    training_data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'training_data.json')

    if os.path.exists(training_data_path):
        with open(training_data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        samples = raw_data if isinstance(raw_data, list) else raw_data.get('samples', [])
        logger.info(f"Loaded {len(samples)} samples from {training_data_path}")
    else:
        logger.warning(f"Training data not found at {training_data_path}, generating synthetic data")
        samples = generate_synthetic_training_data(num_samples=1000, feature_dim=200)

    if not samples:
        raise DataNotFoundError("No training data available", resource="training_data")

    # 创建数据加载器（含验证集拆分）
    train_loader, val_loader = create_data_loaders(
        samples, feature_dim=200, batch_size=request.batchSize, val_split=0.2
    )

    # 初始化模型
    if predictor.model is None:
        field_dims = [200]
        predictor.load_model_from_dims(field_dims)
        logger.info("Model initialized for training")

    # 构建训练配置
    config = TrainingConfig(
        epochs=request.epochs,
        learning_rate=request.learningRate,
        batch_size=request.batchSize,
        dp_enabled=request.dpEnabled,
        dp_epsilon=request.epsilon,
        dp_delta=1e-5,
        dp_sensitivity=1.0,
        val_split=0.0,  # 已手动拆分
        early_stopping_patience=5,
    )

    # 训练
    trainer = ModelTrainer(predictor.model, predictor.device)
    started_at = time.time()
    result = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
    )
    finished_at = time.time()

    # 保存模型
    model_dir = os.path.join(os.path.dirname(__file__), '..', 'saved_models')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'deepfm_trained.pt')
    torch.save(predictor.model.state_dict(), model_path)
    logger.info(f"Model saved to {model_path}")

    # 转换为前端期望的格式
    history = result.get('history', {})
    losses = history.get('loss', [])
    accuracies = history.get('accuracy', [])
    val_losses = history.get('val_loss', [])
    val_accuracies = history.get('val_accuracy', [])

    epsilon_total = result.get('epsilon_spent', 0)
    epochs_completed = result.get('epochs', len(losses))
    epsilon_per_epoch = epsilon_total / max(epochs_completed, 1)

    epochs_data = []
    for i in range(len(losses)):
        epoch_entry = {
            "epochIndex": i,
            "loss": losses[i],
            "accuracy": accuracies[i] * 100,
            "epsilonSpent": epsilon_per_epoch,
        }
        if i < len(val_losses) and val_losses[i] is not None:
            epoch_entry["valLoss"] = val_losses[i]
            epoch_entry["valAccuracy"] = val_accuracies[i] * 100 if i < len(val_accuracies) else None
        epochs_data.append(epoch_entry)

    return {
        "id": int(time.time() * 1000),
        "status": "COMPLETED",
        "totalEpochs": epochs_completed,
        "requestedEpochs": request.epochs,
        "epsilonPerEpoch": round(epsilon_per_epoch, 4),
        "totalEpsilonSpent": round(epsilon_total, 4),
        "earlyStopped": result.get('early_stopped', False),
        "startedAt": started_at,
        "finishedAt": finished_at,
        "durationSeconds": result.get('duration_seconds', 0),
        "epochs": epochs_data
    }


@app.post("/model/load-drugs")
def load_drugs(drugs: List[Dict[str, Any]]):
    if not drugs:
        raise DataValidationError("Drug list must not be empty", field="drugs")
    predictor.set_drugs_data(drugs)
    return {"message": f"Loaded {len(drugs)} drugs", "count": len(drugs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
