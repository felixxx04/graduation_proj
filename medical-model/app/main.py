from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
from app.config import settings
from app.services.predictor import predictor

app = FastAPI(
    title=settings.app_name,
    version="1.0.0"
)

# 药物数据文件路径
DRUGS_DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'drugs_openfda.json')

class DPConfig(BaseModel):
    enabled: bool = True
    epsilon: float = 0.1
    delta: float = 1e-5
    sensitivity: float = 1.0
    noiseMechanism: str = "laplace"
    applicationStage: str = "model"

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

class TrainRequest(BaseModel):
    epochs: int = 10
    learningRate: float = 0.01
    dpEnabled: bool = True
    epsilon: float = 1.0
    batchSize: int = 32

@app.on_event("startup")
async def startup():
    print("Model service starting up...")

    # 加载药物数据
    if os.path.exists(DRUGS_DATA_FILE):
        try:
            with open(DRUGS_DATA_FILE, 'r', encoding='utf-8') as f:
                drugs_data = json.load(f)
            predictor.set_drugs_data(drugs_data)
            print(f"Loaded {len(drugs_data)} drugs from {DRUGS_DATA_FILE}")
        except Exception as e:
            print(f"Failed to load drugs data: {e}")
    else:
        print(f"Drugs data file not found: {DRUGS_DATA_FILE}")

@app.get("/")
def root():
    return {"message": "Medical Recommendation Model Service", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

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
    
    result = predictor.predict(patient_data, request.topK, dp_config)
    return result

@app.post("/model/train")
def train(request: TrainRequest):
    """训练模型"""
    from app.services.trainer import ModelTrainer, DrugRecommendationDataset, generate_synthetic_training_data
    from torch.utils.data import DataLoader
    import os

    try:
        # 准备训练数据
        training_data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'training_data.json')

        if os.path.exists(training_data_path):
            # 加载真实训练数据
            with open(training_data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            samples = raw_data if isinstance(raw_data, list) else raw_data.get('samples', [])
            logger.info(f"Loaded {len(samples)} samples from {training_data_path}")
        else:
            # 生成合成数据
            logger.warning(f"Training data not found at {training_data_path}, generating synthetic data")
            samples = generate_synthetic_training_data(num_samples=1000, feature_dim=200)

        # 创建数据集
        dataset = DrugRecommendationDataset(samples, feature_dim=200)
        train_loader = DataLoader(
            dataset,
            batch_size=request.batchSize,
            shuffle=True,
            num_workers=0
        )

        # 初始化模型（如果未加载）
        if predictor.model is None:
            # 根据数据维度确定 field_dims
            field_dims = [50, 30, 20, 15, 10, 10, 10, 10, 10, 10, 5, 5, 5, 5, 5]
            predictor.load_model_from_dims(field_dims)
            logger.info("Model initialized for training")

        # 准备 DP 配置
        dp_config = None
        if request.dpEnabled:
            dp_config = {
                'enabled': True,
                'epsilon': request.epsilon,
                'delta': 1e-5,
                'sensitivity': 1.0
            }

        # 训练
        trainer = ModelTrainer(predictor.model, predictor.device)
        result = trainer.train(
            train_loader=train_loader,
            epochs=request.epochs,
            learning_rate=request.learningRate,
            dp_config=dp_config,
            batch_size=request.batchSize
        )

        # 保存模型
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'saved_models')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'deepfm_trained.pt')
        torch.save(predictor.model.state_dict(), model_path)
        logger.info(f"Model saved to {model_path}")

        return {
            "message": "Training completed successfully",
            "config": request.dict(),
            "result": result
        }

    except Exception as e:
        logger.error(f"Training failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/model/load-drugs")
def load_drugs(drugs: List[Dict[str, Any]]):
    predictor.set_drugs_data(drugs)
    return {"message": f"Loaded {len(drugs)} drugs", "count": len(drugs)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
