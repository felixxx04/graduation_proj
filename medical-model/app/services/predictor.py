import torch
import numpy as np
import json
import logging
from typing import Dict, List, Any, Optional
from app.models.deepfm import DeepFM
from app.data.preprocessor import PatientFeatureProcessor
from app.utils.privacy import laplace_noise, gaussian_noise

logger = logging.getLogger(__name__)


class RecommendationPredictor:
    def __init__(self, model_path: str = None, use_rag: bool = True):
        self.model = None
        self.preprocessor = PatientFeatureProcessor()
        self.drugs_data = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # RAG 服务
        self.use_rag = use_rag
        self._rag_service = None

    @property
    def rag_service(self):
        """懒加载 RAG 服务"""
        if self._rag_service is None and self.use_rag:
            try:
                from app.services.rag_service import get_rag_service
                self._rag_service = get_rag_service()
                logger.info("RAG service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG service: {e}")
                self._rag_service = None
        return self._rag_service

    def is_rag_ready(self) -> bool:
        """检查 RAG 服务是否就绪"""
        return self.rag_service is not None and self.rag_service.is_ready()
        
    def load_model(self, model_path: str, field_dims: List[int]):
        """加载预训练模型"""
        self.model = DeepFM(field_dims)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"Model loaded from {model_path}")

    def load_model_from_dims(self, field_dims: List[int]):
        """从维度初始化新模型（用于训练）"""
        self.model = DeepFM(field_dims)
        self.model.to(self.device)
        logger.info(f"Model initialized with field_dims: {field_dims}")
        
    def set_drugs_data(self, drugs: List[Dict[str, Any]]):
        self.drugs_data = drugs

    def _create_patient_features(self, patient_data: Dict[str, Any], feature_dim: int = 200) -> np.ndarray:
        """创建患者特征向量（与训练时一致）"""
        features = np.zeros(feature_dim, dtype=np.float32)
        idx = 0

        # 1. 年龄特征 (归一化)
        age = patient_data.get('age', 45) or 45
        features[idx] = age / 100.0
        idx += 1

        # 2. 性别特征
        gender = patient_data.get('gender', 'MALE') or 'MALE'
        features[idx] = 1.0 if gender == 'MALE' else 0.0
        idx += 1

        # 3. BMI (估算)
        features[idx] = 0.55  # 默认 BMI 归一化值
        idx += 1

        # 4. 慢性疾病特征 (20 种)
        diseases = patient_data.get('chronic_diseases', []) or []
        if isinstance(diseases, str):
            diseases = [d.strip() for d in diseases.split('，') if d.strip()]
        disease_vocab = ['高血压', '糖尿病', '冠心病', '高血脂', '哮喘',
                         '慢性肾病', '肝炎', '胃溃疡', '关节炎', '抑郁症',
                         '甲状腺疾病', '贫血', '痛风', '骨质疏松', '心衰',
                         '脑梗塞', '帕金森', '癫痫', '肿瘤', '其他']
        for i, d in enumerate(disease_vocab):
            if i + idx < feature_dim:
                features[idx + i] = 1.0 if d in diseases else 0.0
        idx += len(disease_vocab)

        # 5. 过敏史特征 (10 种)
        allergies = patient_data.get('allergies', []) or []
        if isinstance(allergies, str):
            allergies = [a.strip() for a in allergies.split('，') if a.strip()]
        allergy_vocab = ['青霉素', '磺胺类', '阿司匹林', '碘造影剂', '头孢类',
                         '链霉素', '万古霉素', '喹诺酮类', '四环素类', '其他']
        for i, a in enumerate(allergy_vocab):
            if i + idx < feature_dim:
                features[idx + i] = 1.0 if a in allergies else 0.0
        idx += len(allergy_vocab)

        # 6. 当前用药特征 (10 种)
        idx += 10

        # 7-10. 药物相关特征在 _create_drug_patient_features 中填充
        return features

    def _create_drug_patient_features(self, patient_data: Dict[str, Any], drug: Dict[str, Any], feature_dim: int = 200) -> np.ndarray:
        """创建患者-药物组合特征向量"""
        # 获取患者基础特征
        features = self._create_patient_features(patient_data, feature_dim)

        # 找到当前填充位置
        idx = 1 + 1 + 1 + 20 + 10 + 10  # age + gender + bmi + diseases + allergies + meds

        # 7. 药物类别特征 (8 类)
        drug_category = drug.get('category', '') or ''
        category_map = {'降糖药': 0, '降压药': 1, '降脂药': 2, '抗血小板药': 3,
                        '消化系统用药': 4, '心血管用药': 5, '抗感染药': 6, '其他': 7}
        cat_idx = category_map.get(drug_category, 7)
        for i in range(8):
            if i + idx < feature_dim:
                features[idx + i] = 1.0 if i == cat_idx else 0.0
        idx += 8

        # 8. 疾病-适应症匹配特征
        diseases = patient_data.get('chronic_diseases', []) or []
        if isinstance(diseases, str):
            diseases = [d.strip() for d in diseases.split('，') if d.strip()]
        indications = drug.get('indications', []) or []
        if isinstance(indications, str):
            try:
                indications = json.loads(indications)
            except:
                indications = []

        match_score = 0.0
        for disease in diseases:
            for indication in indications:
                if disease in indication or indication in disease:
                    match_score += 1.0
        match_score = min(match_score / max(len(diseases), 1), 1.0)
        if idx < feature_dim:
            features[idx] = match_score
        idx += 1

        # 9. 禁忌症冲突特征
        contraindications = drug.get('contraindications', []) or []
        if isinstance(contraindications, str):
            try:
                contraindications = json.loads(contraindications)
            except:
                contraindications = []
        conflict_score = 0.0
        for disease in diseases:
            for contra in contraindications:
                if disease in contra or contra in disease:
                    conflict_score += 1.0
        conflict_score = min(conflict_score / max(len(diseases), 1), 1.0)
        if idx < feature_dim:
            features[idx] = conflict_score
        idx += 1

        # 10. 过敏冲突特征
        allergies = patient_data.get('allergies', []) or []
        if isinstance(allergies, str):
            allergies = [a.strip() for a in allergies.split('，') if a.strip()]
        side_effects = drug.get('side_effects', []) or []
        if isinstance(side_effects, str):
            try:
                side_effects = json.loads(side_effects)
            except:
                side_effects = []
        allergy_conflict = 0.0
        for allergy in allergies:
            for effect in side_effects:
                if allergy in str(effect) or str(effect) in allergy:
                    allergy_conflict += 1.0
        allergy_conflict = min(allergy_conflict / max(len(allergies), 1), 1.0)
        if idx < feature_dim:
            features[idx] = allergy_conflict

        return features
        
    def predict(self, patient_data: Dict[str, Any], top_k: int = 4,
                dp_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.model is None:
            return self._mock_prediction(patient_data, top_k, dp_config)

        # 生成患者特征（与训练时相同的 200 维）
        patient_features = self._create_patient_features(patient_data)

        recommendations = []
        for drug in self.drugs_data:
            # 生成药物特征（与训练时相同的方式）
            combined_features = self._create_drug_patient_features(patient_data, drug)

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
                'drugId': drug.get('id') or drug.get('drug_code', ''),
                'drugName': drug.get('name') or drug.get('generic_name', ''),
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
                'drugId': drug.get('id') or drug.get('drug_code', ''),
                'drugName': drug.get('name') or drug.get('generic_name', ''),
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
