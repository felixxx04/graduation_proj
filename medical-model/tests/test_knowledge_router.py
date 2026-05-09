import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.knowledge_router import KnowledgeRouter


@pytest.fixture
def router():
    return KnowledgeRouter()


class TestL1ColloquialMapping:
    def test_拉肚子_routes_to_diarrhea(self, router):
        result = router.route("拉肚子")
        assert result["standard_terms"][0] == "diarrhea"

    def test_感冒_routes_to_uri(self, router):
        result = router.route("感冒")
        assert "upper respiratory infection" in result["standard_terms"]

    def test_unknown_input_fallback_to_raw(self, router):
        result = router.route("莫名其妙")
        assert len(result["standard_terms"]) > 0


class TestL2DiseaseCategory:
    def test_diarrhea_is_gastrointestinal_infectious(self, router):
        result = router.route("拉肚子")
        assert result["body_system"] == "gastrointestinal"
        assert result["etiology"] == "infectious"

    def test_hypertension_is_cardiovascular_chronic(self, router):
        result = router.route("高血压")
        assert result["body_system"] == "cardiovascular"
        assert result["etiology"] == "chronic"


class TestL3ATC:
    def test_gastrointestinal_infectious_routes_correctly(self, router):
        result = router.route("拉肚子")
        assert result["success"]
        drug_classes_str = " ".join(result["drug_classes"])
        assert any(kw in drug_classes_str for kw in ["抗感染", "antibiotic", "抗生素",
            "intestinal anti-infective"])

    def test_respiratory_viral_does_not_get_systemic_antibiotics(self, router):
        result = router.route("感冒")
        assert result["success"]
        has_j01 = any("J01" in code for code in result["atc_codes"])
        assert not has_j01, "Viral URI should not route to systemic antibiotics (J01)"


class TestRoutingPath:
    def test_path_is_traceable(self, router):
        result = router.route("拉肚子")
        assert "L1" in result["routing_path"]
        assert "L2" in result["routing_path"]
        assert result["routing_path"].count("→") >= 2


class TestGetDrugClassFilter:
    def test_drug_class_filter_returns_classes(self, router):
        classes = router.get_drug_class_filter("拉肚子")
        assert len(classes) > 0

    def test_empty_for_unknown_disease(self, router):
        classes = router.get_drug_class_filter("完全不存在的疾病名称")
        assert classes == set()
