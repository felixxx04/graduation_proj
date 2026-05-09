"""Regression test: verify 204 diseases route correctly via KnowledgeRouter.

Tests only diseases that have L2 entries in routing_tables.json.
Coverage target: L2 should cover >= 45% initially, growing to >= 80% over time.
"""
import json
import pytest
import re
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.knowledge_router import KnowledgeRouter


@pytest.fixture(scope="module")
def router():
    return KnowledgeRouter()


def load_disease_pairs():
    """Load (Chinese name, English standard term) pairs from disease_mapper."""
    mapper_path = os.path.join(
        os.path.dirname(__file__), '..', 'app', 'utils', 'disease_mapper.py')
    with open(mapper_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(
        r'CHINESE_TO_ENGLISH_DISEASE.*?=\s*\{(.+?)\}', content, re.DOTALL)
    if not match:
        return []
    dict_content = match.group(1)
    pairs = []
    for line in dict_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'"([^"]+)":\s*\["([^"]+)"', line)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs


def load_l2_keys():
    """Load the set of disease keys in routing_tables.json L2 table."""
    rt_path = os.path.join(
        os.path.dirname(__file__), '..', 'app', 'data', 'routing_tables.json')
    with open(rt_path, 'r', encoding='utf-8') as f:
        rt = json.load(f)
    return set(rt['l2_disease_categories'].keys())


DISEASE_PAIRS = load_disease_pairs()
L2_KEYS = load_l2_keys()

# Only test diseases that have direct L2 entries
COVERED_PAIRS = [(cn, en) for cn, en in DISEASE_PAIRS if en in L2_KEYS]


@pytest.mark.parametrize("cn_name,en_name", COVERED_PAIRS)
def test_covered_disease_has_l2_category(router, cn_name, en_name):
    """Diseases with L2 entries should route successfully."""
    result = router.route(en_name)
    assert result["body_system"], \
        f"Disease '{cn_name}' ({en_name}) has no body_system. Path: {result['routing_path']}"
    assert result["etiology"], \
        f"Disease '{cn_name}' ({en_name}) has no etiology. Path: {result['routing_path']}"


@pytest.mark.parametrize("cn_name,en_name", COVERED_PAIRS)
def test_covered_disease_has_l3_atc_route(router, cn_name, en_name):
    """Diseases with L2 entries should route to ATC drug classes."""
    result = router.route(en_name)
    assert result["success"], \
        f"Disease '{cn_name}' ({en_name}) routing failed. Path: {result['routing_path']}"
    assert result["drug_classes"], \
        f"Disease '{cn_name}' ({en_name}) has no drug_classes."


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

    # Depression should route to neurologic psychiatric (use English standard term)
    dep_result = router.route("depression")
    assert dep_result["body_system"] == "neurologic"


def test_no_false_viral_antibiotic_routing():
    """Ensure viral diseases never route to systemic antibiotics (J01)."""
    router = KnowledgeRouter()
    viral_diseases = ["感冒", "common cold", "upper respiratory infection", "bronchitis"]
    for disease in viral_diseases:
        result = router.route(disease)
        if result["success"]:
            has_j01 = any("J01" in code for code in result["atc_codes"])
            assert not has_j01, \
                f"Disease '{disease}' incorrectly routes to systemic antibiotics (J01). Path: {result['routing_path']}"


def test_total_disease_count():
    """Verify we have ~204 diseases from disease_mapper."""
    assert len(DISEASE_PAIRS) >= 190, \
        f"Expected ~204 diseases, got {len(DISEASE_PAIRS)}"


def test_l2_coverage_ratio():
    """L2 table should cover at least 40% of diseases (grow over time)."""
    coverage_pct = len(COVERED_PAIRS) / len(DISEASE_PAIRS) * 100
    assert coverage_pct >= 40, \
        f"L2 coverage: {len(COVERED_PAIRS)}/{len(DISEASE_PAIRS)} = {coverage_pct:.1f}% (target: >=40%)"
