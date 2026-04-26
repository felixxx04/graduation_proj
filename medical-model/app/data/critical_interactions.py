"""硬编码致命药物交互底线 — 30+确认致命交互对

来源：Drug Finder Interaction warnings + 临床共识（FDA/DrugBank公认）
用途：SafetyFilter Layer 1 确定性硬排除，不受概率模型或DP噪声绕过

原则：宁可误报不遗漏 — 即使患者当前用药列表中包含交互药物，
也必须100%排除此候选药物。
"""

# 确认致命/严重交互对 — (drug_a, drug_b) 无序对
# 所有名称均为小写，匹配时也需转为小写
CRITICAL_INTERACTIONS: set[tuple[str, str]] = {
    # ===== 抗凝/抗血小板类 =====
    ("warfarin", "aspirin"),              # 华法林+阿司匹林：出血风险显著增加
    ("warfarin", "ibuprofen"),            # 华法林+NSAID：出血风险
    ("warfarin", "naproxen"),             # 华法林+NSAID：出血风险
    ("warfarin", "clopidogrel"),          # 华法林+氯吡格雷：出血风险极高
    ("warfarin", "heparin"),              # 华法林+肝素：出血风险叠加
    ("warfarin", "enoxaparin"),           # 华法林+低分子肝素：出血叠加
    ("warfarin", "cefazolin"),            # 华法林+头孢唑林：INR升高+出血
    ("warfarin", "metronidazole"),        # 华法林+甲硝唑：INR显著升高
    ("warfarin", "fluconazole"),          # 华法林+氟康唑：CYP2C9抑制→INR暴增
    ("warfarin", "amiodarone"),           # 华法林+胺碘酮：CYP抑制→出血风险
    ("warfarin", "sulfamethoxazole"),     # 华法林+磺胺甲恶唑：出血风险
    ("warfarin", "phenytoin"),            # 华法林+苯妥英：双向代谢干扰
    ("aspirin", "clopidogrel"),           # 双重抗血小板：出血风险(特定情况需用但需标注)
    ("aspirin", "ibuprofen"),             # 阿司匹林+布洛芬：抗血小板效应抵消+胃出血

    # ===== SSRI/MAOI类 =====
    ("sertraline", "phenelzine"),         # SSRI+MAOI：5-HT综合征→致命
    ("fluoxetine", "phenelzine"),         # SSRI+MAOI：5-HT综合征
    ("paroxetine", "tranylcypromine"),    # SSRI+MAOI：5-HT综合征
    ("citalopram", "isocarboxazid"),      # SSRI+MAOI：5-HT综合征
    ("escitalopram", "phenelzine"),       # SSRI+MAOI：5-HT综合征
    ("fluoxetine", "selegiline"),        # SSRI+MAOI-B：5-HT综合征风险
    ("sertraline", "linezolid"),          # SSRI+利奈唑胺(MAOI性质)：5-HT综合征
    ("fluoxetine", "linezolid"),          # SSRI+利奈唑胺：5-HT综合征

    # ===== 阿片/中枢抑制类 =====
    ("alprazolam", "morphine"),           # 苯二氮卓+阿片：呼吸抑制→昏迷→死亡
    ("lorazepam", "oxycodone"),           # 苯二氮卓+阿片：呼吸抑制
    ("diazepam", "fentanyl"),             # 苯二氮卓+芬太尼：呼吸抑制→死亡
    ("alprazolam", "methadone"),          # 苯二氮卓+美沙酮：呼吸抑制
    ("morphine", "alcohol"),              # 阿片+酒精：呼吸抑制(FDA黑框警告)
    ("oxycodone", "alcohol"),             # 阿片+酒精：呼吸抑制
    ("fentanyl", "alcohol"),              # 芬太尼+酒精：致命呼吸抑制

    # ===== QT延长/心律失常类 =====
    ("amiodarone", "quinidine"),          # 胺碘酮+奎尼丁：QT延长→TdP→致命
    ("sotalol", "amiodarone"),            # 索他洛尔+胺碘酮：QT延长叠加
    ("cisapride", "ketoconazole"),        # 西沙必利+酮康唑：CYP3A4抑制→QT延长→致命
    ("cisapride", "erythromycin"),        # 西沙必利+红霉素：QT延长
    ("pimozide", "ketoconazole"),         # 匹莫齐特+酮康唑：QT延长→致命
    ("haloperidol", "amiodarone"),        # 氟哌啶醇+胺碘酮：QT延长叠加

    # ===== 免疫抑制/感染风险类 =====
    ("adalimumab", "abatacept"),          # TNF阻断剂+CTLA4-Ig：严重感染风险叠加
    ("infliximab", "anakinra"),           # TNF阻断剂+IL-1阻断：严重感染风险
    ("methotrexate", "trimethoprim"),     # 甲氨蝶呤+TMP：骨髓抑制→致命
    ("methotrexate", "sulfamethoxazole-trimethoprim"), # Bactrim+MTX：骨髓抑制

    # ===== 代谢/毒性叠加类 =====
    ("simvastatin", "itraconazole"),      # 辛伐他汀+伊曲康唑：CYP3A4抑制→横纹肌溶解
    ("simvastatin", "clarithromycin"),    # 辛伐他汀+克拉霉素：横纹肌溶解
    ("lovastatin", "ketoconazole"),       # 洛伐他汀+酮康唑：横纹肌溶解
    ("colchicine", "clarithromycin"),     # 秋水仙碱+克拉霉素：秋水仙碱毒性→致命
    ("colchicine", "cyclosporine"),       # 秋水仙碱+环孢素：毒性叠加→致命

    # ===== 器官毒性叠加类 =====
    ("acetaminophen", "alcohol"),         # 对乙酰氨基酚+酒精：肝毒性→急性肝衰竭
    ("acetaminophen", "isoniazid"),       # 对乙酰氨基酚+异烟肼：肝毒性叠加
    ("amphotericin b", "gentamicin"),     # 两性霉素B+庆大霉素：肾毒性叠加→急性肾衰
    ("vancomycin", "gentamicin"),         # 万古霉素+庆大霉素：肾毒性叠加
    ("cisplatin", "aminoglycoside"),      # 顺铂+氨基糖苷：肾毒性叠加→不可逆肾衰

    # ===== 血液学风险 =====
    ("clozapine", "carbamazepine"),       # 氯氮平+卡马西平：粒细胞缺乏风险叠加
    ("trimethoprim", "methotrexate"),     # TMP+MTX：骨髓抑制叠加
}


def get_critical_interactions() -> set[tuple[str, str]]:
    """返回硬编码致命交互对集合"""
    return CRITICAL_INTERACTIONS


def is_critical_interaction(drug_a: str, drug_b: str) -> bool:
    """检查两个药物是否存在致命交互

    Args:
        drug_a: 药物名（大小写不敏感）
        drug_b: 药物名（大小写不敏感）
    Returns:
        True 如果存在致命交互
    """
    pair_a = (drug_a.lower(), drug_b.lower())
    pair_b = (drug_b.lower(), drug_a.lower())
    return pair_a in CRITICAL_INTERACTIONS or pair_b in CRITICAL_INTERACTIONS


def get_interaction_detail(drug_a: str, drug_b: str) -> str | None:
    """获取致命交互的临床说明

    Returns:
        交互说明字符串，如果不存在致命交互则返回 None
    """
    _DETAILS: dict[tuple[str, str], str] = {
        # 补充缺失的临床描述（28/40 对此前无 detail）
    ("warfarin", "naproxen"): "华法林+NSAID→出血风险叠加",
    ("warfarin", "heparin"): "华法林+肝素→出血风险极高（FDA黑框警告）",
    ("warfarin", "enoxaparin"): "华法林+低分子肝素→出血叠加",
    ("warfarin", "cefazolin"): "头孢唑林抑制维生素K依赖凝血→INR升高+出血",
    ("warfarin", "metronidazole"): "甲硝唑抑制CYP2C9→INR显著升高→出血",
    ("warfarin", "fluconazole"): "氟康唑抑制CYP2C9→INR暴增→出血风险",
    ("warfarin", "amiodarone"): "胺碘酮抑制CYP2C9/3A4→华法林代谢减慢→出血",
    ("warfarin", "sulfamethoxazole"): "磺胺甲恶唑抑制华法林代谢→出血风险",
    ("warfarin", "phenytoin"): "苯妥英双向干扰华法林代谢→出血或血栓风险",
    ("aspirin", "clopidogrel"): "双重抗血小板→出血风险（特定情况下需用但需标注）",
    ("aspirin", "ibuprofen"): "布洛芬抵消阿司匹林抗血小板效应+胃出血风险",
    ("paroxetine", "tranylcypromine"): "SSRI+MAOI→5-HT综合征→致命",
    ("citalopram", "isocarboxazid"): "SSRI+MAOI→5-HT综合征→致命",
    ("escitalopram", "phenelzine"): "SSRI+MAOI→5-HT综合征→致命",
    ("fluoxetine", "selegiline"): "SSRI+MAOI-B→5-HT综合征风险",
    ("sertraline", "linezolid"): "SSRI+利奈唑胺(MAOI性质)→5-HT综合征",
    ("fluoxetine", "linezolid"): "SSRI+利奈唑胺→5-HT综合征",
    ("lorazepam", "oxycodone"): "苯二氮卓+阿片→呼吸抑制→昏迷",
    ("diazepam", "fentanyl"): "苯二氮卓+芬太尼→呼吸抑制→死亡（FDA黑框警告）",
    ("alprazolam", "methadone"): "苯二氮卓+美沙酮→呼吸抑制→死亡",
    ("oxycodone", "alcohol"): "阿片+酒精→呼吸抑制→死亡",
    ("fentanyl", "alcohol"): "芬太尼+酒精→致命呼吸抑制",
    ("sotalol", "amiodarone"): "索他洛尔+胺碘酮→QT延长叠加→TdP",
    ("cisapride", "ketoconazole"): "CYP3A4抑制→西沙必利浓度暴增→QT延长→致命",
    ("cisapride", "erythromycin"): "红霉素抑制CYP3A4→西沙必利QT延长→致命",
    ("pimozide", "ketoconazole"): "酮康唑抑制CYP3A4→匹莫齐特QT延长→致命",
    ("haloperidol", "amiodarone"): "氟哌啶醇+胺碘酮→QT延长叠加→致命心律失常",
    ("adalimumab", "abatacept"): "TNF阻断+CTLA4-Ig→严重感染风险叠加",
    ("infliximab", "anakinra"): "TNF阻断+IL-1阻断→严重感染风险叠加",
    ("methotrexate", "sulfamethoxazole-trimethoprim"): "Bactrim+MTX→骨髓抑制叠加→致命",
    ("simvastatin", "clarithromycin"): "克拉霉素抑制CYP3A4→横纹肌溶解→致命",
    ("lovastatin", "ketoconazole"): "酮康唑抑制CYP3A4→洛伐他汀横纹肌溶解→致命",
    ("colchicine", "cyclosporine"): "环孢素抑制P-gp→秋水仙碱毒性叠加→致命",
    ("amphotericin b", "gentamicin"): "两性霉素B+庆大霉素→肾毒性叠加→急性肾衰",
    ("vancomycin", "gentamicin"): "万古霉素+庆大霉素→肾毒性叠加→急性肾衰",
    ("cisplatin", "aminoglycoside"): "顺铂+氨基糖苷→不可逆急性肾衰",
    ("acetaminophen", "isoniazid"): "异烟肼诱导CYP→对乙酰氨基酚肝毒性叠加→急性肝衰竭",
    ("clozapine", "carbamazepine"): "氯氮平+卡马西平→粒细胞缺乏风险叠加",
    ("trimethoprim", "methotrexate"): "TMP+MTX→骨髓抑制叠加→致命",
    # 已有的 12 个保留
    ("warfarin", "aspirin"): "出血风险显著增加（FDA黑框警告）",
    ("warfarin", "ibuprofen"): "NSAID抑制血小板+抗凝叠加→出血风险",
    ("warfarin", "clopidogrel"): "双重抗凝+抗血小板→出血风险极高",
    ("sertraline", "phenelzine"): "SSRI+MAOI→5-HT综合征→致命",
    ("fluoxetine", "phenelzine"): "SSRI+MAOI→5-HT综合征→致命",
    ("alprazolam", "morphine"): "苯二氮卓+阿片→呼吸抑制→昏迷→死亡（FDA黑框警告）",
    ("morphine", "alcohol"): "阿片+酒精→呼吸抑制→死亡",
    ("amiodarone", "quinidine"): "QT延长叠加→尖端扭转→致命心律失常",
    ("simvastatin", "itraconazole"): "CYP3A4抑制→横纹肌溶解→致命",
    ("colchicine", "clarithromycin"): "秋水仙碱毒性叠加→致命",
    ("acetaminophen", "alcohol"): "肝毒性叠加→急性肝衰竭",
    ("methotrexate", "trimethoprim"): "骨髓抑制叠加→致命",
}

    pair_a = (drug_a.lower(), drug_b.lower())
    pair_b = (drug_b.lower(), drug_a.lower())
    return _DETAILS.get(pair_a) or _DETAILS.get(pair_b)


def check_patient_interactions(
    drug_candidate: str, current_medications: list[str],
) -> list[dict[str, str]]:
    """检查候选药物与患者当前用药之间的致命交互

    Args:
        drug_candidate: 候选推荐药物名
        current_medications: 患者当前用药列表
    Returns:
        冲突列表 [{other_drug, detail}]，空列表表示无致命交互
    """
    conflicts = []
    candidate_lower = drug_candidate.lower()

    for med in current_medications:
        if is_critical_interaction(candidate_lower, med.lower()):
            detail = get_interaction_detail(candidate_lower, med.lower())
            conflicts.append({
                'other_drug': med,
                'detail': detail or "确认致命交互",
            })

    return conflicts


def check_cross_candidate_ddi(
    candidate_drugs: list[str],
) -> list[dict[str, str]]:
    """检查推荐候选药物之间的致命交互（两两组合）

    用于推荐列表 top-k 之后的交叉检查，确保推荐药物之间不存在致命交互。

    Args:
        candidate_drugs: 推荐候选药物名称列表（如 top-k 推荐结果）
    Returns:
        冲突列表 [{drug_a, drug_b, detail}]，空列表表示无致命交互
    """
    conflicts = []
    for i in range(len(candidate_drugs)):
        for j in range(i + 1, len(candidate_drugs)):
            a = candidate_drugs[i].lower()
            b = candidate_drugs[j].lower()
            if is_critical_interaction(a, b):
                detail = get_interaction_detail(a, b)
                conflicts.append({
                    'drug_a': candidate_drugs[i],
                    'drug_b': candidate_drugs[j],
                    'detail': detail or "确认致命交互",
                })
    return conflicts