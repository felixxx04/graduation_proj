"""Regression test: verify all 204 diseases route correctly via KnowledgeRouter."""
import pytest
import re
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.knowledge_router import KnowledgeRouter


@pytest.fixture(scope="module")
def router():
    return KnowledgeRouter()


def load_all_diseases():
    """Load all Chinese disease names from disease_mapper."""
    mapper_path = os.path.join(
        os.path.dirname(__file__), '..', 'app', 'utils', 'disease_mapper.py')
    with open(mapper_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(
        r'CHINESE_TO_ENGLISH_DISEASE.*?=\s*\{(.+?)\}', content, re.DOTALL)
    if not match:
        return []
    dict_content = match.group(1)
    diseases = []
    for line in dict_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'"([^"]+)":\s*\[', line)
        if m:
            diseases.append(m.group(1))
    return diseases


ALL_DISEASES = load_all_diseases()


@pytest.mark.parametrize("disease", ALL_DISEASES)
def test_every_disease_has_l2_category(router, disease):
    """Every disease should have L2 body_system + etiology classification."""
    result = router.route(disease)
    assert result["body_system"], \
        f"Disease '{disease}' has no body_system in L2. Path: {result['routing_path']}"
    assert result["etiology"], \
        f"Disease '{disease}' has no etiology in L2. Path: {result['routing_path']}"


@pytest.mark.parametrize("disease", ALL_DISEASES)
def test_every_disease_has_l3_atc_route(router, disease):
    """Every disease should route to at least one ATC drug class."""
    result = router.route(disease)
    assert result["success"], \
        f"Disease '{disease}' routing failed. Path: {result['routing_path']}"
    assert result["drug_classes"], \
        f"Disease '{disease}' has no drug_classes. Body: {result['body_system']}, Etiol: {result['etiology']}"


def test_critical_routing_correctness():
    """Verify known correct routing paths for key diseases."""
    router = KnowledgeRouter()

    # URI/viral should NOT route to systemic antibiotics
    uri_result = router.route("感冒")
    assert "J01" not in uri_result["atc_codes"], \
        "Viral URI should not route to systemic antibiotics"

    # Diarrhea should route to GI anti-infectives
    diarrhea_result = router.route("拉肚子")
    assert diarrhea_result["body_system"] == "gastrointestinal"
    assert diarrhea_result["etiology"] == "infectious"

    # Hypertension should route to cardiovascular chronic
    htn_result = router.route("高血压")
    assert htn_result["body_system"] == "cardiovascular"

    # Depression should route to neurologic psychiatric
    dep_result = router.route("抑郁症")
    assert dep_result["body_system"] == "neurologic"


def test_no_false_viral_antibiotic_routing():
    """Ensure viral diseases never route to systemic antibiotics (J01)."""
    router = KnowledgeRouter()
    viral_diseases = ["感冒", "支气管炎", "上呼吸道感染", "病毒感染"]
    for disease in viral_diseases:
        result = router.route(disease)
        if result["success"]:
            has_j01 = any("J01" in code for code in result["atc_codes"])
            assert not has_j01, \
                f"Disease '{disease}' incorrectly routes to systemic antibiotics (J01). Path: {result['routing_path']}"


def test_total_disease_count():
    """Verify we're testing approximately 204 diseases."""
    assert len(ALL_DISEASES) >= 190, \
        f"Expected ~204 diseases, got {len(ALL_DISEASES)}"
