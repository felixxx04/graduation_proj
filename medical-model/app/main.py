from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.predictor import predictor

app = FastAPI(
    title=settings.app_name,
    version="1.0.0"
)

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
    return {
        "message": "Training not implemented yet",
        "config": request.dict()
    }

@app.post("/model/load-drugs")
def load_drugs(drugs: List[Dict[str, Any]]):
    predictor.set_drugs_data(drugs)
    return {"message": f"Loaded {len(drugs)} drugs", "count": len(drugs)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
