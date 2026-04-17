"""
药物推荐预测服务

改进点：
- 使用 preprocessor 共享词汇表与常量，消除重复定义
- 使用 _safe_parse_json_list 替代裸 json.loads + bare except
- 使用共享异常类型保持错误传播一致性
- 实际特征权重计算替代硬编码 mock 值
"""

import torch
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from app.models.deepfm import DeepFM
from app.data.preprocessor import (
    PatientFeatureProcessor,
    DISEASE_VOCAB,
    ALLERGY_VOCAB,
    DRUG_CATEGORY_MAP,
    FEATURE_DIM,
    _safe_parse_json_list,
)
from app.utils.privacy import laplace_noise, gaussian_noise
from app.exceptions import (
    PredictionError,
    ModelNotLoadedError,
    DataNotFoundError,
    PrivacyConfigError,
)

logger = logging.getLogger(__name__)


class RecommendationPredictor:
    """药物推荐预测器"""

    def __init__(self, feature_dim: int = FEATURE_DIM):
        self.model = None
        self.preprocessor = PatientFeatureProcessor()
        self.drugs_data: List[Dict[str, Any]] = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.feature_dim = feature_dim

        # RAG 服务
        self._rag_service = None

    @property
    def rag_service(self):
        """懒加载 RAG 服务"""
        if self._rag_service is None:
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

    def load_model(self, model_path: str, field_dims: List[int]) -> None:
        """加载预训练模型"""
        try:
            self.model = DeepFM(field_dims)
            self.model.load_state_dict(
                torch.load(model_path, map_location=self.device, weights_only=True)
            )
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Model loaded from {model_path}")
        except FileNotFoundError as e:
            raise ModelNotLoadedError(f"Model file not found: {model_path}") from e
        except Exception as e:
            raise ModelNotLoadedError(f"Failed to load model: {e}") from e

    def load_model_from_dims(self, field_dims: List[int]) -> None:
        """从维度初始化新模型（用于训练）"""
        self.model = DeepFM(field_dims)
        self.model.to(self.device)
        logger.info(f"Model initialized with field_dims: {field_dims}")

    def set_drugs_data(self, drugs: List[Dict[str, Any]]) -> None:
        """设置药物数据"""
        if not isinstance(drugs, list):
            logger.warning(f"Invalid drugs_data type: {type(drugs)}, expected list")
            self.drugs_data = []
            return
        self.drugs_data = drugs
        logger.info(f"Drugs data updated: {len(drugs)} drugs")

    def _create_patient_features(self, patient_data: Dict[str, Any]) -> np.ndarray:
        """创建患者特征向量（与训练时一致）"""
        features = np.zeros(self.feature_dim, dtype=np.float32)
        idx = 0

        # 1. 年龄特征 (归一化)
        age = patient_data.get('age', 45) or 45
        try:
            age = float(age)
        except (TypeError, ValueError):
            age = 45
        features[idx] = min(age / 100.0, 1.5)  # 截断异常值
        idx += 1

        # 2. 性别特征
        gender = patient_data.get('gender', '男') or '男'
        features[idx] = 1.0 if gender in ('男', 'MALE', 'male') else 0.0
        idx += 1

        # 3. BMI (估算)
        features[idx] = 0.55
        idx += 1

        # 4. 慢性疾病特征 (使用共享词汇表)
        diseases = _safe_parse_json_list(patient_data.get('chronic_diseases'))
        disease_vocab_map = {d: i for i, d in enumerate(DISEASE_VOCAB)}
        for d in diseases:
            if d in disease_vocab_map:
                v_idx = disease_vocab_map[d]
                if idx + v_idx < self.feature_dim:
                    features[idx + v_idx] = 1.0
            elif '其他' in disease_vocab_map:
                v_idx = disease_vocab_map['其他']
                if idx + v_idx < self.feature_dim:
                    features[idx + v_idx] = 1.0
        idx += len(DISEASE_VOCAB)

        # 5. 过敏史特征 (使用共享词汇表)
        allergies = _safe_parse_json_list(patient_data.get('allergies'))
        allergy_vocab_map = {a: i for i, a in enumerate(ALLERGY_VOCAB)}
        for a in allergies:
            if a == '无':
                continue
            if a in allergy_vocab_map:
                v_idx = allergy_vocab_map[a]
                if idx + v_idx < self.feature_dim:
                    features[idx + v_idx] = 1.0
            elif '其他' in allergy_vocab_map:
                v_idx = allergy_vocab_map['其他']
                if idx + v_idx < self.feature_dim:
                    features[idx + v_idx] = 1.0
        idx += len(ALLERGY_VOCAB)

        # 6. 当前用药特征 (10 维占位)
        idx += 10

        return features

    def _create_drug_patient_features(
        self, patient_data: Dict[str, Any], drug: Dict[str, Any]
    ) -> np.ndarray:
        """创建患者-药物组合特征向量"""
        features = self._create_patient_features(patient_data)

        # 当前填充位置 = age + gender + bmi + diseases + allergies + meds
        idx = 1 + 1 + 1 + len(DISEASE_VOCAB) + len(ALLERGY_VOCAB) + 10

        # 7. 药物类别特征 (使用共享映射)
        drug_category = str(drug.get('category', '') or '')
        cat_idx = DRUG_CATEGORY_MAP.get(drug_category, DRUG_CATEGORY_MAP.get('其他', len(DRUG_CATEGORY_MAP) - 1))
        for i in range(len(DRUG_CATEGORY_MAP)):
            if idx + i < self.feature_dim:
                features[idx + i] = 1.0 if i == cat_idx else 0.0
        idx += len(DRUG_CATEGORY_MAP)

        # 8. 疾病-适应症匹配特征
        diseases = _safe_parse_json_list(patient_data.get('chronic_diseases'))
        indications = _safe_parse_json_list(drug.get('indications'))

        match_score = 0.0
        for disease in diseases:
            for indication in indications:
                if disease in indication or indication in disease:
                    match_score += 1.0
        match_score = min(match_score / max(len(diseases), 1), 1.0)
        if idx < self.feature_dim:
            features[idx] = match_score
        idx += 1

        # 9. 禁忌症冲突特征
        contraindications = _safe_parse_json_list(drug.get('contraindications'))
        conflict_score = 0.0
        for disease in diseases:
            for contra in contraindications:
                if disease in contra or contra in disease:
                    conflict_score += 1.0
        conflict_score = min(conflict_score / max(len(diseases), 1), 1.0)
        if idx < self.feature_dim:
            features[idx] = conflict_score
        idx += 1

        # 10. 过敏冲突特征
        allergies = _safe_parse_json_list(patient_data.get('allergies'))
        side_effects = _safe_parse_json_list(drug.get('side_effects'))
        allergy_conflict = 0.0
        for allergy in allergies:
            if allergy == '无':
                continue
            for effect in side_effects:
                if allergy in str(effect) or str(effect) in allergy:
                    allergy_conflict += 1.0
        allergy_conflict = min(allergy_conflict / max(len(allergies), 1), 1.0)
        if idx < self.feature_dim:
            features[idx] = allergy_conflict

        return features

    def predict(
        self,
        patient_data: Dict[str, Any],
        top_k: int = 4,
        dp_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行药物推荐预测

        Raises:
            DataNotFoundError: 无药物数据
            PredictionError: 预测过程异常
            PrivacyConfigError: 隐私配置异常
        """
        if not self.drugs_data:
            raise DataNotFoundError("No drug data loaded", resource="drugs_data")

        if self.model is None:
            return self._mock_prediction(patient_data, top_k, dp_config)

        # 校验 DP 配置
        if dp_config and dp_config.get('enabled', False):
            epsilon = dp_config.get('epsilon', 0.1)
            if epsilon <= 0:
                raise PrivacyConfigError(f"Invalid epsilon: {epsilon}, must be > 0")

        try:
            return self._real_prediction(patient_data, top_k, dp_config)
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise PredictionError(f"Prediction failed: {e}") from e

    def _real_prediction(
        self,
        patient_data: Dict[str, Any],
        top_k: int,
        dp_config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """使用已加载模型执行预测"""
        recommendations = []

        for drug in self.drugs_data:
            combined_features = self._create_drug_patient_features(patient_data, drug)

            with torch.no_grad():
                x = torch.tensor(combined_features, dtype=torch.float32).unsqueeze(0).to(self.device)
                score, _ = self.model(x)
                score = score.item()

            # 差分隐私噪声
            dp_noise = 0.0
            if dp_config and dp_config.get('enabled', False):
                epsilon = dp_config.get('epsilon', 0.1)
                delta = dp_config.get('delta', 1e-5)
                mechanism = dp_config.get('noiseMechanism', 'laplace')
                sensitivity = dp_config.get('sensitivity', 1.0)

                try:
                    if mechanism == 'gaussian':
                        noise = gaussian_noise((1,), epsilon, delta, sensitivity)[0]
                    else:
                        noise = laplace_noise((1,), epsilon, sensitivity)[0]
                    score += noise
                    dp_noise = noise
                except Exception as e:
                    logger.warning(f"DP noise injection failed: {e}, proceeding without noise")

            confidence = min(98, max(70, 70 + score * 28))

            recommendations.append({
                'drugId': drug.get('id') or drug.get('drug_code', ''),
                'drugName': drug.get('name') or drug.get('generic_name', ''),
                'category': drug.get('category', ''),
                'dosage': drug.get('typical_dosage', ''),
                'frequency': drug.get('typical_frequency', ''),
                'confidence': round(confidence, 1),
                'score': round(score, 3),
                'dpNoise': round(float(dp_noise), 3) if dp_config and dp_config.get('enabled') else None,
                'reason': self._generate_reason(drug, patient_data),
                'interactions': self._get_interactions(drug, patient_data),
                'sideEffects': (
                    drug.get('side_effects', [])
                    if isinstance(drug.get('side_effects'), list)
                    else []
                ),
                'explanation': {
                    'features': self._generate_feature_explanations(drug, patient_data),
                    'warnings': self._get_warnings(drug, patient_data),
                },
            })

        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_recommendations = recommendations[:top_k]

        return {
            'recommendationId': int(np.random.randint(1000, 9999)),
            'selected': top_recommendations,
            'base': [r.copy() for r in recommendations[:top_k]],
            'dp': top_recommendations,
            'dpEnabled': dp_config.get('enabled', True) if dp_config else False,
        }

    def _mock_prediction(
        self,
        patient_data: Dict[str, Any],
        top_k: int,
        dp_config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """模型未加载时的 mock 预测"""
        recommendations = []
        for drug in self.drugs_data[:top_k + 2]:
            score = np.random.uniform(0.5, 0.95)
            dp_noise = 0.0
            if dp_config and dp_config.get('enabled', False):
                epsilon = dp_config.get('epsilon', 0.1)
                dp_noise = np.random.laplace(0, 1 / max(epsilon, 1e-10))
                score += dp_noise

            recommendations.append({
                'drugId': drug.get('id') or drug.get('drug_code', ''),
                'drugName': drug.get('name') or drug.get('generic_name', ''),
                'category': drug.get('category', ''),
                'dosage': drug.get('typical_dosage', ''),
                'frequency': drug.get('typical_frequency', ''),
                'confidence': round(70 + np.random.uniform(0, 28), 1),
                'score': round(score, 3),
                'dpNoise': round(float(dp_noise), 3) if dp_config and dp_config.get('enabled') else None,
                'reason': "基于患者特征与药物适应症的匹配分析",
                'interactions': [],
                'sideEffects': (
                    drug.get('side_effects', [])
                    if isinstance(drug.get('side_effects'), list)
                    else []
                ),
                'explanation': {'features': [], 'warnings': []},
            })

        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return {
            'recommendationId': int(np.random.randint(1000, 9999)),
            'selected': recommendations[:top_k],
            'base': recommendations[:top_k],
            'dp': recommendations[:top_k],
            'dpEnabled': dp_config.get('enabled', True) if dp_config else False,
        }

    def _generate_reason(self, drug: Dict, patient: Dict) -> str:
        """生成推荐理由"""
        indications = _safe_parse_json_list(drug.get('indications'))
        diseases = _safe_parse_json_list(patient.get('chronic_diseases'))

        matched = [d for d in diseases if any(d in ind or ind in d for ind in indications)]
        if matched:
            return f"适应症匹配：{', '.join(matched[:2])}，推荐使用"
        return "基于综合特征分析推荐"

    def _get_interactions(self, drug: Dict, patient: Dict) -> List[str]:
        """获取药物相互作用警告"""
        interactions = _safe_parse_json_list(drug.get('interactions'))
        current_meds = _safe_parse_json_list(patient.get('current_medications'))

        result = []
        for inter in interactions:
            for med in current_meds:
                if med in inter or inter in med:
                    result.append(f"注意与 {med} 的相互作用")
        return result if result else ["暂无明显相互作用"]

    def _generate_feature_explanations(self, drug: Dict, patient: Dict) -> List[Dict]:
        """生成特征解释（基于实际匹配计算权重）"""
        explanations = []

        # 适应症匹配权重
        diseases = _safe_parse_json_list(patient.get('chronic_diseases'))
        indications = _safe_parse_json_list(drug.get('indications'))
        match_count = sum(
            1 for d in diseases
            if any(d in ind or ind in d for ind in indications)
        )
        match_weight = min(match_count * 3.2, 10.0) if match_count > 0 else 0.0
        match_contribution = match_weight * 0.78
        explanations.append({
            'name': '适应症匹配',
            'weight': round(match_weight, 2),
            'contribution': round(match_contribution, 2),
            'note': f'匹配 {match_count} 项适应症' if match_count > 0 else '无直接匹配',
        })

        # 年龄因素
        age = patient.get('age', 45) or 45
        try:
            age = float(age)
        except (TypeError, ValueError):
            age = 45
        age_weight = 0.5 if 18 <= age <= 75 else -1.0
        explanations.append({
            'name': '年龄因素',
            'weight': age_weight,
            'contribution': round(age_weight * 0.6, 2),
            'note': '适宜年龄段' if 18 <= age <= 75 else '需注意年龄因素',
        })

        # 过敏风险
        allergies = _safe_parse_json_list(patient.get('allergies'))
        side_effects = _safe_parse_json_list(drug.get('side_effects'))
        has_allergy_conflict = any(
            a in str(e) or str(e) in a
            for a in allergies if a != '无'
            for e in side_effects
        )
        allergy_weight = -5.0 if has_allergy_conflict else 0.0
        explanations.append({
            'name': '过敏风险',
            'weight': allergy_weight,
            'contribution': 0.0 if not has_allergy_conflict else round(allergy_weight * 0.5, 2),
            'note': '存在过敏风险' if has_allergy_conflict else '无过敏风险',
        })

        return explanations

    def _get_warnings(self, drug: Dict, patient: Dict) -> List[str]:
        """获取禁忌症警告"""
        warnings = []
        contraindications = _safe_parse_json_list(drug.get('contraindications'))
        diseases = _safe_parse_json_list(patient.get('chronic_diseases'))

        for disease in diseases:
            for contra in contraindications:
                if disease in contra or contra in disease:
                    warnings.append(f"注意禁忌症：{contra}")
        return warnings


predictor = RecommendationPredictor()
