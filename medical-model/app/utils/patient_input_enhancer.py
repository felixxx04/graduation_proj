"""Patient input enhancer — normalizes colloquial Chinese disease descriptions.

Three-tier fallback:
  L1: Exact match in colloquial mapping table
  L2: Keyword-based fuzzy matching against a medical keyword dictionary
  L3: Symptom combination pattern matching (from symptom_combos.json)
  Fallback: Single-character matching as last resort

Returns (standard_disease_name, confidence_level) where confidence is "high"|"medium"|"low"|"none"
"""
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class PatientInputEnhancer:
    """Normalize colloquial patient input to standard medical terms."""

    def __init__(self) -> None:
        # Load L1 colloquial map from routing tables
        with open(os.path.join(_DATA_DIR, "routing_tables.json"), "r", encoding="utf-8") as f:
            self.colloquial_map: Dict[str, List[str]] = json.load(f)["l1_colloquial_to_standard"]

        # Load L3 symptom combo patterns
        with open(os.path.join(_DATA_DIR, "symptom_combos.json"), "r", encoding="utf-8") as f:
            self.symptom_combos: List[dict] = json.load(f)["combos"]

        # L2 keyword dictionary — medical keywords to likely standard terms
        self.keywords: Dict[str, List[str]] = {
            "喉咙": ["pharyngitis", "upper respiratory infection"],
            "嗓子": ["pharyngitis", "upper respiratory infection"],
            "咳嗽": ["cough"],
            "痰": ["productive cough"],
            "发热": ["fever"],
            "发烧": ["fever"],
            "头痛": ["headache"],
            "头疼": ["headache"],
            "腹泻": ["diarrhea"],
            "拉肚": ["diarrhea"],
            "便秘": ["constipation"],
            "恶心": ["nausea"],
            "呕吐": ["vomiting"],
            "胃": ["gastritis", "gastroesophageal reflux disease"],
            "腹痛": ["abdominal pain"],
            "肚子": ["abdominal pain"],
            "腰痛": ["low back pain"],
            "腰酸": ["low back pain"],
            "关节": ["joint pain", "osteoarthritis"],
            "睡不着": ["insomnia"],
            "睡不": ["insomnia"],
            "失眠": ["insomnia"],
            "焦虑": ["anxiety"],
            "紧张": ["anxiety"],
            "烦躁": ["anxiety"],
            "心慌": ["palpitations", "arrhythmia"],
            "胸闷": ["chest tightness"],
            "胸痛": ["chest pain"],
            "气短": ["dyspnea"],
            "喘": ["dyspnea", "asthma"],
            "水肿": ["edema"],
            "浮肿": ["edema"],
            "皮疹": ["rash"],
            "痒": ["pruritus", "itching"],
            "小便": ["urinary tract infection"],
            "尿": ["urinary tract infection"],
            "鼻炎": ["allergic rhinitis"],
            "感冒": ["common cold", "upper respiratory infection"],
            "头晕": ["dizziness", "vertigo"],
            "乏力": ["fatigue"],
            "疲劳": ["fatigue"],
        }

    def enhance(self, raw_input: str) -> Tuple[Optional[str], str]:
        """Normalize patient input to a standard disease name.

        Args:
            raw_input: Patient's raw description (Chinese, may be colloquial/multi-symptom)

        Returns:
            (standard_disease_name, confidence_level)
            standard_disease_name is None if all tiers fail
            confidence_level is "high" | "medium" | "low" | "none"
        """
        text = raw_input.strip()
        if not text:
            return None, "none"

        # L1: Exact match in colloquial table
        exact_match = self.colloquial_map.get(text)
        if exact_match:
            logger.info("ENHANCER L1 exact: '%s' -> %s", text, exact_match[0])
            return exact_match[0], "high"

        # Try without trailing particles (了, 啊, 啦, 呀, 的, 呢, 吧, 吗)
        for particle in ["了", "啊", "啦", "呀", "的", "呢", "吧", "吗"]:
            if text.endswith(particle) and len(text) > 1:
                trimmed = text[:-1]
                exact_match = self.colloquial_map.get(trimmed)
                if exact_match:
                    logger.info("ENHANCER L1 trimmed: '%s' -> %s", text, exact_match[0])
                    return exact_match[0], "high"

        # L2: Keyword matching (greedy — longest keywords first)
        matched_terms: List[str] = []
        sorted_keywords = sorted(self.keywords.keys(), key=len, reverse=True)
        for kw in sorted_keywords:
            if kw in text:
                matched_terms.extend(self.keywords[kw])

        if matched_terms:
            # Prefer the most specific term (longest string)
            best = max(matched_terms, key=len)
            logger.info("ENHANCER L2 keyword: '%s' -> '%s' (matched: %s)", text, best, set(matched_terms))
            return best, "medium"

        # L3: Symptom combination pattern matching
        for combo in self.symptom_combos:
            hits = sum(1 for kw in combo["keywords"] if kw in text)
            if hits >= combo["min_matches"]:
                logger.info(
                    "ENHANCER L3 combo: '%s' -> '%s' (%d/%d hits)",
                    text, combo["disease"], hits, len(combo["keywords"]),
                )
                return combo["disease"], "low"

        # Fallback: single character matching
        for char in text:
            if char in self.keywords and self.keywords[char]:
                logger.info("ENHANCER fallback char: '%s' -> '%s'", text, self.keywords[char][0])
                return self.keywords[char][0], "low"

        logger.warning("ENHANCER all tiers failed for: '%s'", text)
        return None, "none"


_enhancer_instance: Optional[PatientInputEnhancer] = None


def get_enhancer() -> PatientInputEnhancer:
    """Get or create the singleton PatientInputEnhancer instance."""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = PatientInputEnhancer()
    return _enhancer_instance
