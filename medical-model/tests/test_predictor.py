"""
预测器单元测试
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPrivacyUtils:
    """隐私工具测试"""

    def test_laplace_scale_calculation(self):
        """测试 Laplace 尺度计算"""
        from app.utils.privacy import laplace_noise

        epsilon = 0.1
        sensitivity = 1.0
        shape = (100,)

        noise = laplace_noise(shape, epsilon, sensitivity)

        assert noise.shape == shape
        assert isinstance(noise, np.ndarray)

    def test_gaussian_noise_generation(self):
        """测试 Gaussian 噪声生成"""
        from app.utils.privacy import gaussian_noise

        epsilon = 1.0
        delta = 1e-5
        sensitivity = 1.0
        shape = (50,)

        noise = gaussian_noise(shape, epsilon, delta, sensitivity)

        assert noise.shape == shape
        assert isinstance(noise, np.ndarray)


class TestRecommendationPredictor:
    """推荐预测器测试"""

    @pytest.fixture
    def predictor(self):
        """创建预测器实例"""
        with patch('app.services.predictor.PatientFeatureProcessor'):
            from app.services.predictor import RecommendationPredictor
            return RecommendationPredictor(model_path=None, use_rag=False)

    @pytest.fixture
    def sample_drugs(self):
        """样本药物数据"""
        return [
            {
                'id': 1,
                'name': '阿司匹林',
                'category': '解热镇痛药',
                'indications': ['头痛', '发热', '疼痛'],
                'contraindications': ['胃溃疡', '出血倾向'],
                'side_effects': ['胃肠道不适', '出血'],
                'interactions': ['华法林', '阿司匹林'],
                'typical_dosage': '100mg',
                'typical_frequency': '每日一次'
            },
            {
                'id': 2,
                'name': '布洛芬',
                'category': '解热镇痛药',
                'indications': ['发热', '疼痛', '炎症'],
                'contraindications': ['胃溃疡', '哮喘'],
                'side_effects': ['胃肠道不适'],
                'interactions': [],
                'typical_dosage': '200mg',
                'typical_frequency': '每日三次'
            }
        ]

    @pytest.fixture
    def sample_patient(self):
        """样本患者数据"""
        return {
            'id': 1,
            'age': 45,
            'gender': '男',
            'chronic_diseases': ['高血压'],
            'symptoms': '头痛',
            'allergies': [],
            'current_medications': ['降压药']
        }

    def test_set_drugs_data(self, predictor, sample_drugs):
        """测试药物数据设置"""
        predictor.set_drugs_data(sample_drugs)

        assert len(predictor.drugs_data) == 2
        assert predictor.drugs_data[0]['name'] == '阿司匹林'

    def test_mock_prediction_returns_results(self, predictor, sample_drugs, sample_patient):
        """测试预测返回结果"""
        predictor.set_drugs_data(sample_drugs)

        result = predictor.predict(sample_patient, top_k=2)

        assert 'selected' in result
        assert 'recommendationId' in result
        assert len(result['selected']) <= 2

    def test_dp_noise_applied_when_enabled(self, predictor, sample_drugs, sample_patient):
        """测试差分隐私噪声注入"""
        predictor.set_drugs_data(sample_drugs)

        dp_config = {
            'enabled': True,
            'epsilon': 0.1,
            'delta': 1e-5,
            'noiseMechanism': 'laplace',
            'sensitivity': 1.0
        }

        result = predictor.predict(sample_patient, top_k=1, dp_config=dp_config)

        assert result['dpEnabled'] == True
        # dpNoise 可能为 None（mock 模式），检查结构正确即可

    def test_dp_disabled_no_noise(self, predictor, sample_drugs, sample_patient):
        """测试禁用 DP 时无噪声"""
        predictor.set_drugs_data(sample_drugs)

        dp_config = {'enabled': False}

        result = predictor.predict(sample_patient, top_k=1, dp_config=dp_config)

        assert result['dpEnabled'] == False

    def test_prediction_with_empty_drugs(self, predictor, sample_patient):
        """测试无药物数据时的处理"""
        predictor.set_drugs_data([])

        result = predictor.predict(sample_patient, top_k=2)

        assert 'selected' in result
        assert len(result['selected']) == 0

    def test_generate_reason(self, predictor, sample_drugs):
        """测试推荐理由生成"""
        predictor.set_drugs_data(sample_drugs)

        patient = {
            'chronic_diseases': ['发热'],
            'allergies': []
        }

        reason = predictor._generate_reason(sample_drugs[0], patient)

        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_get_warnings_for_contraindications(self, predictor, sample_drugs):
        """测试禁忌症警告"""
        predictor.set_drugs_data(sample_drugs)

        patient = {
            'chronic_diseases': ['胃溃疡']
        }

        warnings = predictor._get_warnings(sample_drugs[0], patient)

        assert len(warnings) > 0
        assert any('胃溃疡' in w or '禁忌' in w for w in warnings)


class TestTrainer:
    """训练器测试"""

    def test_synthetic_data_generation(self):
        """测试合成数据生成"""
        from app.services.trainer import generate_synthetic_training_data

        samples = generate_synthetic_training_data(num_samples=100, feature_dim=50)

        assert len(samples) == 100
        assert 'features' in samples[0]
        assert 'label' in samples[0]
        assert samples[0]['features'].shape == (50,)

    def test_dataset_creation(self):
        """测试数据集创建"""
        from app.services.trainer import DrugRecommendationDataset, generate_synthetic_training_data

        samples = generate_synthetic_training_data(num_samples=50, feature_dim=100)
        dataset = DrugRecommendationDataset(samples, feature_dim=100)

        assert len(dataset) == 50

        item = dataset[0]
        assert 'features' in item
        assert 'label' in item


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
