"""Clinical knowledge routing engine — deterministic disease→drug-class routing.

Four-level routing:
  L1: Colloquial → Standard medical term
  L2: Standard term → Body system + Etiology
  L3: Body system + Etiology → ATC drug class / drug_classes
  L4: Drug class → Specific drug candidates (delegated to predictor)

Architecture: Router sits BEFORE the existing 3-layer pipeline.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class KnowledgeRouter:
    """Deterministic disease→drug-class routing using clinical knowledge tables."""

    def __init__(self, routing_tables_path: Optional[str] = None):
        if routing_tables_path is None:
            routing_tables_path = os.path.join(_DATA_DIR, "routing_tables.json")
        with open(routing_tables_path, "r", encoding="utf-8") as f:
            tables = json.load(f)
        self.l1_map: Dict[str, List[str]] = tables["l1_colloquial_to_standard"]
        self.l2_map: Dict[str, dict] = tables["l2_disease_categories"]
        self.l3_map: Dict[str, dict] = tables["l3_indication_to_atc"]
        logger.info(
            f"KnowledgeRouter loaded: L1=%d terms, L2=%d diseases, L3=%d routes",
            len(self.l1_map), len(self.l2_map), len(self.l3_map),
        )

    def route(self, chinese_disease: str, confidence: str = "high") -> dict:
        """Full L1→L2→L3 routing for a Chinese disease name.

        Returns:
            dict with keys: success, routing_path, standard_terms, body_system,
            etiology, atc_codes, drug_classes, confidence
        """
        result = {
            "success": False,
            "routing_path": "",
            "standard_terms": [],
            "body_system": "",
            "etiology": "",
            "atc_codes": [],
            "drug_classes": [],
            "confidence": confidence,
        }

        # L1: Colloquial → Standard
        key = chinese_disease.strip()
        standard_terms = self.l1_map.get(key, [])
        if not standard_terms:
            standard_terms = self.l1_map.get(key.lower(), [])

        if standard_terms:
            result["standard_terms"] = standard_terms
            result["routing_path"] = f"L1({key}→{standard_terms[0]})"
        else:
            standard_terms = [key.lower().replace(" ", "_")]
            result["standard_terms"] = standard_terms
            result["routing_path"] = f"L1({key}→{standard_terms[0]}[fallback])"

        # L2: Standard term → Body system + Etiology
        std_term = standard_terms[0]
        category = self.l2_map.get(std_term)
        if not category:
            for l2_key, l2_val in self.l2_map.items():
                if std_term in l2_key or l2_key in std_term:
                    category = l2_val
                    result["routing_path"] += f"→L2({l2_key}[fuzzy])"
                    break

        if category:
            result["body_system"] = category["body_system"]
            result["etiology"] = category["etiology"]
            if "[fuzzy]" not in result["routing_path"]:
                result["routing_path"] += f"→L2({category['category_name']})"
            result["success"] = True
        else:
            result["routing_path"] += "→L2(NOT_FOUND)"
            return result

        # L3: Body system + Etiology → ATC drug classes
        route_key = f"{category['body_system']}_{category['etiology']}"
        atc_info = self.l3_map.get(route_key)
        if atc_info:
            result["atc_codes"] = atc_info["atc_codes"]
            result["drug_classes"] = atc_info["drug_classes"]
            result["routing_path"] += f"→L3({route_key})"
        else:
            result["routing_path"] += f"→L3(NOT_FOUND:{route_key})"
            result["success"] = False

        return result

    def get_drug_class_filter(self, chinese_disease: str, confidence: str = "high") -> Set[str]:
        """Get set of drug class keywords appropriate for this disease.

        Used to filter/re-rank drug candidates before DeepFM scoring.
        Returns empty set if routing fails.
        """
        route = self.route(chinese_disease, confidence)
        if not route["success"]:
            return set()
        classes = set()
        synonyms = {
            "ACE抑制剂": "ace inhibitor",
            "ARB": "arb angiotensin receptor blocker",
            "钙通道阻滞剂": "calcium channel blocker",
            "β受体阻断剂": "beta blocker",
            "利尿剂": "diuretic",
            "抗生素": "antibiotic",
            "抗真菌药": "antifungal",
            "抗病毒药": "antiviral",
            "抗血小板药": "antiplatelet",
            "抗凝药": "anticoagulant",
            "他汀类": "statin",
            "PPI": "proton pump inhibitor",
            "H2RA": "h2 receptor antagonist",
            "NSAIDs": "nonsteroidal anti-inflammatory drug",
            "糖皮质激素": "corticosteroid",
            "胰岛素": "insulin",
            "降糖药": "antidiabetic",
            "SSRI": "selective serotonin reuptake inhibitor",
            "SNRI": "serotonin norepinephrine reuptake inhibitor",
            "苯二氮卓类": "benzodiazepine",
            "抗精神病药": "antipsychotic",
            "抗癫痫药": "antiepileptic",
            "多巴胺激动剂": "dopamine agonist",
            "抗组胺药": "antihistamine",
            "解热镇痛药": "analgesic antipyretic",
            "镇咳药": "antitussive",
            "祛痰药": "expectorant",
            "支气管扩张剂": "bronchodilator",
            "降尿酸药": "uricosuric",
            "双膦酸盐": "bisphosphonate",
            "雌激素": "estrogen",
            "孕激素": "progestin",
            "升压药": "vasopressor",
            "血管活性药": "vasoactive",
            "抗心律失常药": "antiarrhythmic",
            "硝酸酯类": "nitrate",
            "贝特类": "fibrate",
            "甲状腺激素": "thyroid hormone",
            "抗甲状腺药": "antithyroid",
            "减充血剂": "decongestant",
            "青霉素类": "penicillin",
            "大环内酯类": "macrolide",
            "氟喹诺酮类": "fluoroquinolone",
            "头孢菌素类": "cephalosporin",
            "抗纤维化药": "antifibrotic",
            "免疫抑制剂": "immunosuppressant",
            "肺动脉高压专用药": "pah therapy",
            "血管扩张剂": "vasodilator",
            "胃黏膜保护剂": "gastric mucosal protectant",
            "促动力药": "prokinetic",
            "肠道抗感染药": "intestinal anti-infective",
            "氨基水杨酸类": "aminosalicylate",
            "生物制剂": "biologic",
            "泻药": "laxative",
            "止泻药": "antidiarrheal",
            "解痉药": "antispasmodic",
            "益生菌": "probiotic",
            "保肝药": "hepatoprotective",
            "降脂药": "lipid lowering",
            "利胆药": "choleretic",
            "镇痛药": "analgesic",
            "曲普坦类": "triptan",
            "CGRP拮抗剂": "cgrp antagonist",
            "MAOI": "maoi monoamine oxidase inhibitor",
            "胆碱酯酶抑制剂": "cholinesterase inhibitor",
            "NMDA拮抗剂": "nmda antagonist",
            "促红细胞生成素": "erythropoietin",
            "泌尿系统抗菌药": "urinary antibacterial",
            "排石药": "stone dissolution",
            "别嘌呤醇": "allopurinol",
            "碱化尿液药": "urine alkalinizer",
            "DMARDs": "dmard disease modifying antirheumatic drug",
            "软骨保护剂": "chondroprotective",
            "秋水仙碱": "colchicine",
            "唑类": "azole",
            "多烯类": "polyene",
            "铁剂": "iron supplement",
            "维生素B12": "vitamin b12",
            "叶酸": "folic acid",
            "避孕药": "contraceptive",
            "促性腺激素": "gonadotropin",
            "抗寄生虫药": "antiparasitic",
            "降眼压药": "intraocular pressure lowering",
            "碳酸酐酶抑制剂": "carbonic anhydrase inhibitor",
            "前列腺素类似物": "prostaglandin analogue",
            "人工泪液": "artificial tears",
            "抗氧化剂（辅助）": "antioxidant adjuvant",
            "外用糖皮质激素": "topical corticosteroid",
            "润肤剂": "emollient",
            "钙调神经磷酸酶抑制剂": "calcineurin inhibitor",
            "外用维生素D类似物": "topical vitamin d analogue",
            "解热镇痛药（对症）": "analgesic antipyretic symptomatic",
        }
        for dc in route["drug_classes"]:
            classes.add(dc.lower())
            for zh, en in synonyms.items():
                if zh.lower() == dc.lower() or zh.lower() in dc.lower():
                    classes.add(en.lower())
                if dc.lower() == zh.lower() or dc.lower() in zh.lower():
                    classes.add(en.lower())
        return classes


_router_instance: Optional[KnowledgeRouter] = None


def get_router() -> KnowledgeRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = KnowledgeRouter()
    return _router_instance
