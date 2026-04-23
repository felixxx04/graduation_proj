from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import time
import logging
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
    version="2.0.0"
)

# ── 全局异常处理 ──

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


# ── 请求模型 ──

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
        if v not in ('laplace', 'gaussian', 'geometric'):
            raise ValueError('noiseMechanism must be "laplace", "gaussian", or "geometric"')
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
    learningRate: float = 0.001
    dpEnabled: bool = True
    epsilon: float = 1.0
    batchSize: int = 128
    lambdaContra: float = 2.0

    @field_validator('epochs')
    @classmethod
    def validate_epochs(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError('epochs must be in [1, 100]')
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
        if v < 32 or v > 256:
            raise ValueError('batchSize must be in [32, 256]')
        return v

    @field_validator('lambdaContra')
    @classmethod
    def validate_lambda_contra(cls, v: float) -> float:
        if v < 1.0 or v > 10.0:
            raise ValueError('lambdaContra must be in [1.0, 10.0]')
        return v


# ── 端点 ──

@app.on_event("startup")
async def startup():
    logger.info("Model service starting up...")
    logger.info("Waiting for drug data via /model/load-drugs endpoint")


@app.get("/")
def root():
    return {"message": "Medical Recommendation Model Service", "status": "running", "version": "2.0.0"}


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
        "modelVersion": None,
        "modelTrainedAt": None,
        "fieldDims": predictor.field_dims,
        "diseasesCount": 0,
        "kgDrugsCount": len(predictor.drugs_data),
        "contraindicationCount": 0,
        "disclaimer": "本推荐结果由AI模型生成，仅供参考，不构成医疗诊断或处方建议",
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
                'noiseMechanism': 'laplace',
            }

    return predictor.predict(patient_data, request.topK, dp_config)


@app.post("/model/train")
def train(request: TrainRequest):
    """训练端点 — 当前为占位实现，等待数据集和训练管道完成后启用"""
    raise TrainingError("Training pipeline not yet implemented. Please provide training dataset first.")


@app.post("/model/load-drugs")
def load_drugs(drugs: List[Dict[str, Any]]):
    if not drugs:
        raise DataValidationError("Drug list must not be empty", field="drugs")
    predictor.set_drugs_data(drugs)
    return {"message": f"Loaded {len(drugs)} drugs", "count": len(drugs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)