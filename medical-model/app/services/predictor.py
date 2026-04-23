"""药物推荐预测服务 — 清理后骨架版本"""

import torch
import numpy as np
import logging
from typing import Dict, List, Any, Optional
from app.models.deepfm import DeepFM
from app.utils.privacy import laplace_noise, gaussian_noise
from app.exceptions import (
    PredictionError,
    ModelNotLoadedError,
    DataNotFoundError,
    PrivacyConfigError,
)

logger = logging.getLogger(__name__)


class RecommendationPredictor:
    """药物推荐预测器（骨架版本）"""

    def __init__(self):
        self.model: Optional[DeepFM] = None
        self.field_dims: Optional[List[int]] = None
        self.drugs_data: List[Dict[str, Any]] = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def load_model(self, model_path: str, field_dims: List[int]) -> None:
        """加载预训练模型"""
        try:
            self.field_dims = field_dims
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

    def init_model(self, field_dims: List[int]) -> None:
        """初始化新模型（用于训练）"""
        self.field_dims = field_dims
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

    def predict(
        self,
        patient_data: Dict[str, Any],
        top_k: int = 4,
        dp_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行药物推荐预测"""
        if not self.drugs_data:
            raise DataNotFoundError("No drug data loaded", resource="drugs_data")

        if self.model is None:
            return self._mock_prediction(patient_data, top_k, dp_config)

        if dp_config and dp_config.get('enabled', False):
            epsilon = dp_config.get('epsilon', 0.1)
            if epsilon <= 0:
                raise PrivacyConfigError(f"Invalid epsilon: {epsilon}, must be > 0")

        try:
            return self._mock_prediction(patient_data, top_k, dp_config)
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise PredictionError(f"Prediction failed: {e}") from e

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
                sensitivity = dp_config.get('sensitivity', 1.0)
                mechanism = dp_config.get('noiseMechanism', 'laplace')
                delta = dp_config.get('delta', 1e-5)

                if mechanism == 'gaussian':
                    noise = gaussian_noise((1,), epsilon, delta, sensitivity)[0]
                else:
                    noise = laplace_noise((1,), epsilon, sensitivity)[0]
                dp_noise = float(noise)
                score += dp_noise

            side_effects = drug.get('side_effects', [])
            if not isinstance(side_effects, list):
                side_effects = []

            recommendations.append({
                'drugId': drug.get('id', 0),
                'drugName': drug.get('name', ''),
                'category': drug.get('category', ''),
                'dosage': drug.get('typical_dosage', ''),
                'frequency': drug.get('typical_frequency', ''),
                'confidence': round(70 + np.random.uniform(0, 28), 1),
                'score': round(float(score), 3),
                'dpNoise': round(dp_noise, 3) if dp_config and dp_config.get('enabled') else None,
                'reason': "基于患者特征与药物适应症的匹配分析",
                'interactions': [],
                'sideEffects': side_effects,
                'matchedDisease': None,
                'explanation': {'features': [], 'warnings': []},
            })

        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_recommendations = recommendations[:top_k]

        # 构建 base（无 DP）和 dp（有 DP）对比
        base_recommendations = []
        dp_recommendations = []
        for rec in top_recommendations:
            base_rec = dict(rec)
            base_rec['dpNoise'] = None
            base_recommendations.append(base_rec)
            dp_recommendations.append(rec)

        return {
            'recommendationId': int(np.random.randint(1000, 9999)),
            'selected': top_recommendations,
            'base': base_recommendations,
            'dp': dp_recommendations,
            'dpEnabled': dp_config.get('enabled', True) if dp_config else False,
            'excludedDrugs': [],
            'inferredDiseases': [],
            'allDiseases': [],
            'totalCandidates': len(self.drugs_data),
            'totalExcluded': 0,
        }


predictor = RecommendationPredictor()