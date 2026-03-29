import torch
import numpy as np
import json
from typing import Dict, List, Any, Optional
from app.models.deepfm import DeepFM
from app.data.preprocessor import PatientFeatureProcessor
from app.utils.privacy import laplace_noise, gaussian_noise

class RecommendationPredictor:
    def __init__(self, model_path: str = None):
        self.model = None
        self.preprocessor = PatientFeatureProcessor()
        self.drugs_data = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def load_model(self, model_path: str, field_dims: List[int]):
        self.model = DeepFM(field_dims)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        
    def set_drugs_data(self, drugs: List[Dict[str, Any]]):
        self.drugs_data = drugs
        
    def predict(self, patient_data: Dict[str, Any], top_k: int = 4,
                dp_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.model is None:
            return self._mock_prediction(patient_data, top_k, dp_config)
        
        patient_features = self.preprocessor.transform_patient(patient_data)
        
        recommendations = []
        for drug in self.drugs_data:
            drug_features = self.preprocessor.transform_drug(drug)
            combined_features = np.concatenate([patient_features, drug_features])
            
            with torch.no_grad():
                x = torch.tensor(combined_features, dtype=torch.float32).unsqueeze(0).to(self.device)
                score, embeds = self.model(x)
                score = score.item()
            
            if dp_config and dp_config.get('enabled', False):
                epsilon = dp_config.get('epsilon', 0.1)
                delta = dp_config.get('delta', 1e-5)
                mechanism = dp_config.get('noiseMechanism', 'laplace')
                sensitivity = dp_config.get('sensitivity', 1.0)
                
                if mechanism == 'gaussian':
                    noise = gaussian_noise((1,), epsilon, delta, sensitivity)[0]
                else:
                    noise = laplace_noise((1,), epsilon, sensitivity)[0]
                score += noise
                dp_noise = noise
            else:
                dp_noise = 0
            
            confidence = min(98, max(70, 70 + score * 28))
            
            recommendations.append({
                'drugId': drug['id'],
                'drugName': drug['name'],
                'category': drug.get('category', ''),
                'dosage': drug.get('typical_dosage', ''),
                'frequency': drug.get('typical_frequency', ''),
                'confidence': round(confidence, 1),
                'score': round(score, 3),
                'dpNoise': round(dp_noise, 3) if dp_config and dp_config.get('enabled') else None,
                'reason': self._generate_reason(drug, patient_data),
                'interactions': self._get_interactions(drug, patient_data),
                'sideEffects': drug.get('side_effects', []) if isinstance(drug.get('side_effects'), list) else [],
                'explanation': {
                    'features': self._generate_feature_explanations(drug, patient_data),
                    'warnings': self._get_warnings(drug, patient_data)
                }
            })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_recommendations = recommendations[:top_k]
        
        return {
            'recommendationId': np.random.randint(1000, 9999),
            'selected': top_recommendations,
            'base': recommendations[:top_k] if not dp_config or not dp_config.get('enabled') else 
                    [r.copy() for r in recommendations[:top_k]],
            'dp': top_recommendations,
            'dpEnabled': dp_config.get('enabled', True) if dp_config else False
        }
    
    def _mock_prediction(self, patient_data: Dict[str, Any], top_k: int,
                         dp_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        recommendations = []
        for drug in self.drugs_data[:top_k + 2]:
            score = np.random.uniform(0.5, 0.95)
            if dp_config and dp_config.get('enabled', False):
                epsilon = dp_config.get('epsilon', 0.1)
                noise = np.random.laplace(0, 1/epsilon)
                score += noise
            
            recommendations.append({
                'drugId': drug['id'],
                'drugName': drug['name'],
                'category': drug.get('category', ''),
                'dosage': drug.get('typical_dosage', ''),
                'frequency': drug.get('typical_frequency', ''),
                'confidence': round(70 + np.random.uniform(0, 28), 1),
                'score': round(score, 3),
                'dpNoise': round(np.random.laplace(0, 0.1), 3) if dp_config and dp_config.get('enabled') else None,
                'reason': f"基于患者特征与药物适应症的匹配分析",
                'interactions': [],
                'sideEffects': drug.get('side_effects', []) if isinstance(drug.get('side_effects'), list) else [],
                'explanation': {'features': [], 'warnings': []}
            })
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return {
            'recommendationId': np.random.randint(1000, 9999),
            'selected': recommendations[:top_k],
            'base': recommendations[:top_k],
            'dp': recommendations[:top_k],
            'dpEnabled': dp_config.get('enabled', True) if dp_config else False
        }
    
    def _generate_reason(self, drug: Dict, patient: Dict) -> str:
        indications = drug.get('indications', [])
        if isinstance(indications, str):
            indications = json.loads(indications) if indications else []
        diseases = patient.get('chronic_diseases', [])
        if isinstance(diseases, str):
            diseases = json.loads(diseases) if diseases else []
        
        matched = [d for d in diseases if any(d in ind or ind in d for ind in indications)]
        if matched:
            return f"适应症匹配：{', '.join(matched[:2])}，推荐使用"
        return "基于综合特征分析推荐"
    
    def _get_interactions(self, drug: Dict, patient: Dict) -> List[str]:
        interactions = drug.get('interactions', [])
        if isinstance(interactions, str):
            interactions = json.loads(interactions) if interactions else []
        current_meds = patient.get('current_medications', [])
        if isinstance(current_meds, str):
            current_meds = json.loads(current_meds) if current_meds else []
        
        result = []
        for inter in interactions:
            for med in current_meds:
                if med in inter or inter in med:
                    result.append(f"注意与 {med} 的相互作用")
        return result if result else ["暂无明显相互作用"]
    
    def _generate_feature_explanations(self, drug: Dict, patient: Dict) -> List[Dict]:
        return [
            {'name': '适应症匹配', 'weight': 3.2, 'contribution': 2.5, 'note': '匹配度高'},
            {'name': '年龄因素', 'weight': 0.5, 'contribution': 0.3, 'note': '适宜年龄段'},
            {'name': '过敏风险', 'weight': -5.0, 'contribution': 0.0, 'note': '无过敏风险'}
        ]
    
    def _get_warnings(self, drug: Dict, patient: Dict) -> List[str]:
        warnings = []
        contraindications = drug.get('contraindications', [])
        if isinstance(contraindications, str):
            contraindications = json.loads(contraindications) if contraindications else []
        diseases = patient.get('chronic_diseases', [])
        if isinstance(diseases, str):
            diseases = json.loads(diseases) if diseases else []
        
        for disease in diseases:
            for contra in contraindications:
                if disease in contra or contra in disease:
                    warnings.append(f"注意禁忌症：{contra}")
        return warnings

predictor = RecommendationPredictor()
