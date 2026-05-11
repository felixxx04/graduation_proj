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
from app.utils.patient_input_enhancer import get_enhancer
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
    sensitivity: float = 0.2  # sigmoid输出[0,1]的实证灵敏度
    noiseMechanism: str = "laplace"
    applicationStage: str = "model"

    @field_validator('epsilon')
    @classmethod
    def validate_epsilon(cls, v: float) -> float:
        if v < 0.01 or v > 10.0:
            raise ValueError('epsilon must be in [0.01, 10.0] for meaningful privacy protection')
        return v

    @field_validator('delta')
    @classmethod
    def validate_delta(cls, v: float) -> float:
        if v <= 0 or v >= 1:
            raise ValueError('delta must be in (0, 1)')
        return v

    @field_validator('sensitivity')
    @classmethod
    def validate_sensitivity(cls, v: float) -> float:
        if v < 0.01 or v > 1.0:
            raise ValueError('sensitivity must be in [0.01, 1.0] for sigmoid output [0,1]')
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

    # v2: 患者器官功能与生理指标（由后端自动补充，前端不手动填写）
    renal_function: Optional[str] = None     # normal/mild/moderate/severe/unknown
    hepatic_function: Optional[str] = None   # normal/mild/moderate/severe/unknown
    bmi: Optional[float] = None
    bmi_group: Optional[str] = None          # underweight/normal/overweight/obese/unknown
    pregnancy_status: Optional[str] = None   # pregnant/not_pregnant/unknown
    breastfeeding_status: Optional[str] = None  # breastfeeding/not_breastfeeding/unknown
    smoking_status: Optional[str] = None     # never/former/current/unknown
    drinking_status: Optional[str] = None    # none/occasional/regular/heavy/unknown
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    fasting_glucose: Optional[float] = None
    hba1c: Optional[float] = None
    cholesterol_total: Optional[float] = None
    cholesterol_ldl: Optional[float] = None
    heart_rate: Optional[int] = None
    # 患者输入增强（由 PatientInputEnhancer 在 predict 中填充）
    enhanced_disease: Optional[str] = None
    enhanced_diseases: Optional[List[str]] = None
    input_confidence: Optional[str] = None

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
        if v < 0.01 or v > 10.0:
            raise ValueError('epsilon must be in [0.01, 10.0]')
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
    # ── Patient Input Enhancement ──
    # Normalize colloquial Chinese to standard medical terms
    enhancer = get_enhancer()
    raw_disease = getattr(request, 'diseases', '')
    if raw_disease and isinstance(raw_disease, str) and raw_disease.strip():
        enhanced_disease, confidence = enhancer.enhance(raw_disease)
        if enhanced_disease:
            logger.info(f"Enhanced input: '{raw_disease}' -> '{enhanced_disease}' (confidence={confidence})")
            request.enhanced_disease = enhanced_disease
            request.input_confidence = confidence
        else:
            request.input_confidence = "none"
    elif isinstance(raw_disease, list) and raw_disease:
        enhanced_list = []
        confidences = []
        for d in raw_disease:
            ed, conf = enhancer.enhance(str(d))
            if ed:
                enhanced_list.append(ed)
                confidences.append(conf)
        if enhanced_list:
            request.enhanced_diseases = enhanced_list
            confidence_rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
            request.input_confidence = min(confidences, key=lambda c: confidence_rank.get(c, 0))

    # 处理疾病和症状: 中文→英文映射 + 症状→疾病映射
    from app.utils.disease_mapper import process_patient_input, _split_input, translate_chinese_disease

    # 生成综合疾病名集合（包含中文翻译+症状关联）
    expanded_diseases = process_patient_input(
        diseases_str=request.diseases or "",
        symptoms_str=request.symptoms or "",
    )

    # 保存原始映射结果（不含vocab代理词），用于识别患者真实疾病
    # SEMANTIC_VOCAB_MAP添加的是vocab代理词，不是患者实际疾病
    original_mapped_diseases = expanded_diseases.copy()  # 语义映射前的原始集合

    # 记录患者主要输入疾病（不含扩展同义词）
    # 用于lost_diseases计算：只识别用户实际输入的疾病，而非disease_mapper扩展的同义词
    # 例: "cluster headache" 扩展为 ["cluster headache", "head pain", "tension headache", ...]
    #     primary_input_diseases 只包含 "cluster headache"，避免lost_diseases过度膨胀
    primary_input_diseases: Set[str] = set()
    if request.diseases:
        disease_parts = _split_input(request.diseases or "")
        for part in disease_parts:
            en_names = translate_chinese_disease(part)
            if en_names:
                # 中文输入：取第一个翻译（通常是直接映射，最精确）
                primary_input_diseases.add(en_names[0])
            else:
                # 英文输入：直接用输入本身作为主疾病
                primary_input_diseases.add(part.strip().lower())

    # 语义映射：将不在vocab中的疾病名映射到语义最接近的vocab词
    # 这些映射用于vocab过滤阶段，确保模型编码有意义
    # 注意：适应症匹配层（clinical_matcher）独立于vocab，仍使用原始英文匹配
    SEMANTIC_VOCAB_MAP = {
        "hypothyroidism": "hyperthyroidism",  # vocab中仅有hyperthyroidism
        "constipation": "stomach pain",        # vocab中无constipation
        "bronchitis": "asthma",                # vocab中无bronchitis
        "menopause": "depression",             # vocab中无menopause
        "atrial fibrillation": "arrhythmia",   # vocab中无atrial_fibrillation
        "copd": "asthma",                      # vocab中无copd
        "chronic obstructive pulmonary disease": "asthma",
        "enteritis": "bacterial infections",   # vocab中无enteritis，映射到感染类
        "colitis": "bacterial infections",     # vocab中无colitis，映射到感染类
        "cholecystitis": "stomach pain",       # 胆囊炎映射到腹痛（更接近真实症状）
        "cholelithiasis": "stomach pain",      # 胆结石映射到腹痛
        "gallstones": "stomach pain",
        "biliary colic": "stomach pain",
        "urinary calculi": "bacterial urinary tract infection",  # 尿路结石映射到UTI
        "kidney stones": "bacterial urinary tract infection",
        "nephrolithiasis": "bacterial urinary tract infection",
        "common cold": "common cold",          # 已在vocab，确保映射
        "viral infection": "bacterial infections",    # vocab中无viral infection
        "viral illness": "bacterial infections",
        "fungal infection": "bacterial infections",   # vocab中无fungal infection
        "candidiasis": "bacterial infections",
        "cervicitis": "bacterial infections",          # vocab中无cervicitis
        "vaginitis": "bacterial infections",            # vocab中无vaginitis
        "vulvovaginal candidiasis": "bacterial infections",
        "bacterial vaginosis": "bacterial infections",
        "pelvic inflammatory disease": "bacterial infections",
        "adnexitis": "bacterial infections",
        "pelvic pain": "stomach pain",                  # vocab中无pelvic pain
        "dry eye syndrome": "allergic rhinitis",        # vocab中无dry eye
        "keratoconjunctivitis sicca": "allergic rhinitis",
        "obsessive compulsive disorder": "anxiety",     # vocab中无OCD，映射到焦虑类
        "ocd": "anxiety",
        "pulmonary fibrosis": "asthma",                 # vocab中无pulmonary fibrosis
        "idiopathic pulmonary fibrosis": "asthma",
        "cataract": "glaucoma",                         # vocab中无cataract，映射到眼科类
        "alcohol dependence": "anxiety",                # vocab中无alcohol dependence
        "alcoholism": "anxiety",
        "alcohol withdrawal": "anxiety",
        "menstrual irregularity": "anxiety",             # vocab中无menstrual irregularity
        "dysmenorrhea": "stomach pain",                  # vocab中无dysmenorrhea
        "colon cancer": "breast cancer",                 # vocab中无colon cancer
        "colorectal cancer": "breast cancer",
        "lung cancer": "breast cancer",                  # vocab中无lung cancer
        "prostate cancer": "breast cancer",              # vocab中无prostate cancer
        "thyroid cancer": "hyperthyroidism",             # vocab中无thyroid cancer
        "appendicitis": "stomach pain",                  # vocab中无appendicitis
        "abdominal pain": "stomach pain",
        "parotitis": "bacterial infections",             # vocab中无parotitis
        "mumps": "bacterial infections",
        "tonsillitis": "bacterial infections",           # vocab中无tonsillitis
        "otitis media": "bacterial infections",          # vocab中无otitis media
        "prostatitis": "bacterial infections",           # vocab中无prostatitis
        "poisoning": "bacterial infections",             # vocab中无poisoning
        "toxicity": "bacterial infections",
        "herpes simplex virus infection": "bacterial infections",  # vocab中无HSV
        "menopausal symptoms": "depression",
        "nicotine dependence": "anxiety",
    }
    # Apply semantic mapping before vocab filter
    mapped_diseases = set()
    for d in expanded_diseases:
        d_lower = d.lower()
        if d_lower in SEMANTIC_VOCAB_MAP:
            mapped_diseases.add(SEMANTIC_VOCAB_MAP[d_lower])
            mapped_diseases.add(d)  # 保留原始名（用于适应症匹配）
        else:
            mapped_diseases.add(d)
    expanded_diseases = mapped_diseases

    # 保存原始映射结果（含不在vocab中的词），用于适应症匹配
    # 关键修复：indication_match_conditions必须排除SEMANTIC_VOCAB_MAP的代理词
    # 代理词（如constipation→"stomach pain"）仅用于模型编码，不应影响临床匹配
    # 否则PPI等通过"stomach pain"适应症匹配到便秘患者
    proxy_values = set(SEMANTIC_VOCAB_MAP.values())
    all_mapped_diseases = set()
    for d in expanded_diseases:
        if d.lower() not in proxy_values:
            all_mapped_diseases.add(d)
        # 代理词跳过 — 它们不是患者的真实疾病

    # 过滤：只保留 encoder primary_disease 词表中存在的疾病名
    # 避免 "pyrexia"/"febrile illness" 等未登录词映射到 __unknown__ 导致模型退化
    vocab_filtered = set()
    if predictor.encoder is not None and 'primary_disease' in predictor.encoder.vocab_maps:
        pd_vocab = predictor.encoder.vocab_maps['primary_disease']
        known = sorted([d for d in expanded_diseases if d in pd_vocab])
        unknown = [d for d in expanded_diseases if d not in pd_vocab]
        if known:
            vocab_filtered = set(known)
            if unknown:
                logger.info(f"Filtered unknown disease synonyms: {unknown} (not in encoder vocab)")
        elif unknown:
            # Fallback: 尝试子串匹配在vocab中找最接近的词
            fallback_matches = []
            for d in unknown:
                d_lower = d.lower()
                for vocab_word in pd_vocab:
                    vocab_lower = vocab_word.lower()
                    if d_lower in vocab_lower or vocab_lower in d_lower:
                        fallback_matches.append(vocab_word)
            if fallback_matches:
                vocab_filtered = set(fallback_matches)
                logger.info(f"Fallback substring match for unknown diseases {unknown} → {sorted(fallback_matches)}")
            else:
                logger.warning(f"All expanded diseases unknown in encoder vocab: {unknown}, using as-is")
                vocab_filtered = set(expanded_diseases)
    else:
        logger.warning("Encoder or primary_disease vocab not available, using expanded_diseases as-is")
        vocab_filtered = set(expanded_diseases)

    expanded_diseases = sorted(vocab_filtered)

    # 基本疾病列表（从 diseases 字段分割）
    disease_list = _split_input(request.diseases or "")

    patient_data = {
        'id': request.patientId,
        'age': request.age,
        'gender': request.gender,
        'diseases': expanded_diseases,  # vocab过滤后的疾病名（用于模型编码）
        'disease_list': disease_list,  # 原始输入（用于解释）
        'chronic_diseases': expanded_diseases,  # 同步
        'indication_match_conditions': all_mapped_diseases,  # 完整映射结果（用于适应症匹配）
        'original_mapped_diseases': original_mapped_diseases,  # 语义映射前的原始疾病（用于识别真实疾病）
        'primary_input_diseases': primary_input_diseases,  # 患者实际输入的疾病（不含扩展同义词）
        'symptoms': request.symptoms,
        'allergies': request.allergies.split('，') if request.allergies else [],
        'current_medications': request.currentMedications.split('，') if request.currentMedications else [],
        # 患者输入增强字段（由PatientInputEnhancer在predict入口处添加）
        'enhanced_disease': getattr(request, 'enhanced_disease', None),
        'enhanced_diseases': getattr(request, 'enhanced_diseases', None),
        'input_confidence': getattr(request, 'input_confidence', None),
    }

    # v2: 患者器官功能与生理指标（由后端自动补充）
    v2_fields = {
        'renal_function': request.renal_function,
        'hepatic_function': request.hepatic_function,
        'bmi': request.bmi,
        'bmi_group': request.bmi_group,
        'pregnancy_status': request.pregnancy_status,
        'pregnancy': request.pregnancy_status,  # 别名（safety_filter兼容）
        'breastfeeding_status': request.breastfeeding_status,
        'smoking_status': request.smoking_status,
        'drinking_status': request.drinking_status,
        'blood_pressure_systolic': request.blood_pressure_systolic,
        'blood_pressure_diastolic': request.blood_pressure_diastolic,
        'fasting_glucose': request.fasting_glucose,
        'hba1c': request.hba1c,
        'cholesterol_total': request.cholesterol_total,
        'cholesterol_ldl': request.cholesterol_ldl,
        'heart_rate': request.heart_rate,
    }
    # 仅将非None的v2字段加入patient_data（None会覆盖record_builder的默认值）
    for key, val in v2_fields.items():
        if val is not None:
            patient_data[key] = val

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