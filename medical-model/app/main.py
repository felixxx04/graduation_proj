from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import json
import time
import logging
from pathlib import Path
from app.config import settings
from app.services.predictor import predictor
from app.data.critical_interactions import get_critical_interactions
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
    epsilon: float = 1.0  # v2: 统一默认值1.0
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
    userId: Optional[str] = None

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
    batchSize: int = 256
    focalLossAlpha: float = 0.25
    focalLossGamma: float = 2.0

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
        if v < 32 or v > 512:
            raise ValueError('batchSize must be in [32, 512]')
        return v


# ── 端点 ──

@app.on_event("startup")
async def startup():
    """v2: startup加载pipeline_data.json中的safety数据"""
    logger.info("Model service starting up...")

    # 加载pipeline_data.json中的安全数据
    pipeline_path = Path(settings.data_dir) / "pipeline_data.json"
    if pipeline_path.exists():
        try:
            with open(pipeline_path, 'r', encoding='utf-8') as f:
                pipeline_data = json.load(f)

            contraindication_map = pipeline_data.get('contraindication_map', {})
            interaction_map = pipeline_data.get('interaction_map', {})
            critical_interactions = get_critical_interactions()

            predictor.set_safety_data(
                contraindication_map, interaction_map, critical_interactions
            )

            # 加载药物数据 (Drug Finder核心718药物)
            merged_drugs = pipeline_data.get('merged_drugs', {})
            drugs_list = list(merged_drugs.values())
            predictor.set_drugs_data(drugs_list)

            logger.info(
                f"Startup loaded: {len(contraindication_map)} contraindication entries, "
                f"{len(interaction_map)} interaction entries, "
                f"{len(critical_interactions)} critical pairs, "
                f"{len(drugs_list)} drugs"
            )
        except Exception as e:
            logger.error(f"Failed to load pipeline_data.json: {e}", exc_info=True)
            logger.warning("Safety data not loaded — SafetyFilter will only use critical_interactions")
    else:
        logger.warning(f"pipeline_data.json not found at {pipeline_path}")

    # 自动加载已保存的模型和encoder
    saved_models_dir = Path(settings.saved_models_dir)
    best_model_path = saved_models_dir / "best_model.pt"
    encoder_path = saved_models_dir / "encoder.json"
    metadata_path = saved_models_dir / "metadata.json"

    if best_model_path.exists() and encoder_path.exists():
        try:
            # 从metadata读取field_dims
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                field_dims = meta.get('field_dims')
            else:
                field_dims = None

            if field_dims:
                predictor.load_model(str(best_model_path), field_dims)
                predictor.load_encoder(str(encoder_path))
                logger.info(f"Auto-loaded model and encoder from {saved_models_dir}")
            else:
                logger.warning("metadata.json missing field_dims — skip auto-load model")
        except Exception as e:
            logger.error(f"Failed to auto-load model: {e}", exc_info=True)
    else:
        logger.info("No saved model/encoder found — running in demo mode until training")


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
        "drugsCount": len(predictor.drugs_data),
        "contraindicationCount": len(predictor.contraindication_map),
        "interactionCount": len(predictor.interaction_map),
        "criticalInteractionsCount": len(predictor.critical_interactions),
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

    return predictor.predict(patient_data, request.topK, dp_config, request.userId)


@app.post("/model/train")
def train(request: TrainRequest):
    """训练端点 — 使用DeepFMTrainer进行训练

    注意: 训练需要先加载pipeline_data.json中的safety/indication数据
    和模拟患者数据。当前为异步训练入口。
    """
    if not predictor.drugs_data:
        raise DataNotFoundError("No drug data loaded — call /model/load-drugs first", resource="drugs_data")

    # 训练需要完整的pipeline数据
    from app.pipeline.runner import PipelineRunner
    from app.models.trainer import DeepFMTrainer
    import json
    from pathlib import Path

    pipeline_path = Path(settings.data_dir) / "pipeline_data.json"
    if not pipeline_path.exists():
        raise DataNotFoundError("pipeline_data.json not found — cannot generate training data", resource="pipeline_data")

    # 加载pipeline数据
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        pipeline_data = json.load(f)

    runner = PipelineRunner()
    runner.load_safety_data(
        pipeline_data.get('contraindication_map', {}),
        pipeline_data.get('interaction_map', {}),
    )
    runner.load_indication_data(
        pipeline_data.get('indication_map', {}),
    )

    # 使用pipeline_data中的merged_drugs作为药物数据
    merged_drugs = pipeline_data.get('merged_drugs', {})
    drugs_list = list(merged_drugs.values())

    # 模拟患者数据: 从pipeline_data中的patient_records取 (如果没有则用基本模拟)
    patient_records = pipeline_data.get('patient_records', [])
    if not patient_records:
        raise DataNotFoundError("No patient_records in pipeline_data.json — cannot train", resource="patient_records")

    # 运行pipeline生成训练数据
    pipeline_result = runner.run(patient_records, drugs_list, seed=42)

    # 训练
    trainer = DeepFMTrainer(
        field_dims=pipeline_result['field_dims'],
        dp_enabled=request.dpEnabled,
        dp_target_epsilon=request.epsilon,
        focal_alpha=request.focalLossAlpha,
        focal_gamma=request.focalLossGamma,
    )

    train_metadata = trainer.train(
        train_dataset=pipeline_result['train_dataset'],
        val_dataset=pipeline_result['val_dataset'],
        epochs=request.epochs,
        learning_rate=request.learningRate,
        batch_size=request.batchSize,
    )

    # 保存并加载encoder
    from pathlib import Path as P
    encoder_path = P(settings.saved_models_dir) / "encoder.json"
    pipeline_result['encoder'].save(str(encoder_path))
    predictor.load_encoder(str(encoder_path))

    # 加载训练好的模型到predictor
    best_model_path = P(settings.saved_models_dir) / "best_model.pt"
    predictor.load_model(str(best_model_path), pipeline_result['field_dims'])

    return {
        "message": "Training completed",
        "bestEpoch": train_metadata['best_epoch'],
        "bestValLoss": train_metadata['best_val_loss'],
        "dpEpsilonSpent": train_metadata.get('dp_epsilon_spent'),
        "historyLength": len(train_metadata['train_history']),
        "modelVersion": train_metadata['model_version'],
    }


@app.post("/model/load-drugs")
def load_drugs(drugs: List[Dict[str, Any]]):
    if not drugs:
        raise DataValidationError("Drug list must not be empty", field="drugs")
    predictor.set_drugs_data(drugs)
    return {"message": f"Loaded {len(drugs)} drugs", "count": len(drugs)}


# ── 隐私预算端点 ──

@app.get("/model/privacy/budget")
def privacy_budget_status(userId: Optional[str] = None):
    """查询隐私预算状态"""
    from app.utils.privacy_budget import get_all_tracker_status, get_budget_tracker
    if userId:
        tracker = get_budget_tracker(userId)
        status = tracker.get_status()
        return {
            "userId": userId,
            "epsilonBudget": status.epsilon_total_budget,
            "epsilonSpent": round(status.epsilon_spent_cumulative, 6),
            "epsilonSpentNaive": round(status.epsilon_spent_naive, 6),
            "deltaBudget": status.delta_total_budget,
            "deltaSpent": status.delta_spent_cumulative,
            "queryCount": status.query_count,
            "warningLevel": status.warning_level.value,
            "remainingRatio": round(status.remaining_budget_ratio, 4),
        }
    return get_all_tracker_status()


@app.post("/model/privacy/budget/reset")
def reset_privacy_budget(userId: str):
    """重置指定用户的隐私预算"""
    from app.utils.privacy_budget import reset_budget_tracker
    reset_budget_tracker(userId)
    return {"message": f"Budget reset for user={userId}"}


# ── 审计日志端点 ──

@app.get("/model/audit/logs")
def query_audit_logs(
    limit: int = 20,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """查询审计日志

    支持单日查询(date)或跨日范围查询(start_date + end_date)。
    最多查询31天范围。
    """
    from app.utils.audit_logger import get_audit_logger
    audit = get_audit_logger()
    records = audit.query_recent(
        limit=limit, date=date, start_date=start_date, end_date=end_date,
    )
    return {"count": len(records), "records": records}


class ConsentRequest(BaseModel):
    userId: str
    consentGiven: bool
    dpConfig: Optional[DPConfig] = None
    requestId: Optional[str] = None


@app.post("/model/audit/consent")
def log_consent(request: ConsentRequest):
    """记录知情同意确认"""
    from app.utils.audit_logger import get_audit_logger
    audit = get_audit_logger()
    dp_dict = request.dpConfig.dict() if request.dpConfig else None
    path = audit.log_consent(
        user_id=request.userId,
        consent_given=request.consentGiven,
        dp_config=dp_dict,
        request_id=request.requestId,
    )
    consent_id = Path(path).stem  # e.g. "consent_a1b2c3d4"
    return {"message": "Consent logged", "consentId": consent_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)