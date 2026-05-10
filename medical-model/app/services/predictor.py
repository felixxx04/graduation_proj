"""药物推荐预测服务 — 三层架构版本

Layer 1: SafetyFilter（确定性硬排除）→ 不受DP噪声影响
Layer 2: RuleMarker（规则标记）→ 附加临床警告
Layer 3: DeepFM排序（个性化排序）→ DP噪声仅作用于此层
"""

import uuid
import torch
import numpy as np
import logging
from typing import Dict, List, Set, Tuple, Any, Optional

from app.models.deepfm import DeepFM
from app.pipeline.feature_encoder import FeatureEncoder
from app.services.safety_filter import SafetyFilter, RuleMarker
from app.utils.privacy import laplace_noise, gaussian_noise
from app.utils.feedback_learner import get_feedback_learner
from app.utils.privacy_budget import get_budget_tracker, BudgetWarningLevel
from app.utils.clinical_matcher import match_indication
from app.pipeline.record_builder import build_feature_record
from app.services.explanation_generator import generate_explanation
from app.data.critical_interactions import check_cross_candidate_ddi, is_critical_interaction
from app.utils.drug_translator import build_translation_cache, translate_drug_name
from app.utils.translation_mapper import get_mapper as get_translation_mapper
from app.exceptions import (
    PredictionError,
    ModelNotLoadedError,
    DataNotFoundError,
    PrivacyConfigError,
)

logger = logging.getLogger(__name__)


def _apply_dp_noise(
    raw_score: float,
    dp_config: Optional[Dict[str, Any]],
    has_indication: bool = False,
) -> Tuple[float, float, bool, Optional[Dict[str, Any]]]:
    """计算DP噪声并返回 (final_score, dp_noise, dp_anomaly, dp_confidence)

    DP噪声应用流程 (v3: 双层防护):
    1. 临床安全阈值: raw_score < 0.15 的药物直接归零 (公开阈值，DP后处理定理允许)
       - 无适应症药物(base_score=0.05)不会被噪声推升到高分
       - 阈值是公开参数，不依赖隐私数据，不违反DP保证
    2. 根据噪声机制(Laplace/Gaussian)计算噪声值
    3. final_score = raw_score + dp_noise
    4. 截断: 下界0, 上界max(1.0, raw_score+0.35) — 防止噪声放大超过信号3.5倍
    5. dp_anomaly用于UI显示: 噪声显著改变排序方向时标记警告
    """
    # 第一层防护: 临床安全阈值 (公开阈值, 不违反DP后处理定理)
    # raw_score < 0.15 说明药物几乎无适应症证据, 噪声不应将其推升为"推荐"
    # 例外: 有适应症匹配的药物豁免此阈值 — 临床金标准优先于模型不确定
    CLINICAL_THRESHOLD = 0.15
    if raw_score < CLINICAL_THRESHOLD and not has_indication:
        return 0.0, 0.0, False, None

    dp_noise = 0.0
    dp_confidence = None

    if dp_config and dp_config.get('enabled', False):
        epsilon = dp_config.get('epsilon', 1.0)
        sensitivity = dp_config.get('sensitivity', 0.2)
        mechanism = dp_config.get('noiseMechanism', 'laplace')
        delta = dp_config.get('delta', 1e-5)

        if mechanism == 'gaussian':
            noise = gaussian_noise((1,), epsilon, delta, sensitivity)[0]
            # Gaussian 95% CI: ±1.96·σ, σ = sensitivity·√(2·ln(1.25/δ))/ε
            import math
            sigma = sensitivity * math.sqrt(2.0 * math.log(1.25 / delta)) / epsilon
            ci_half = 1.96 * sigma
        else:
            noise = laplace_noise((1,), epsilon, sensitivity)[0]
            # Laplace 精确95% CI: ±(-b·ln(0.05)) = ±(scale * 2.996)
            scale = sensitivity / epsilon
            import math
            ci_half = -scale * math.log(0.05)  # ≈ 2.996 * scale

        dp_noise = float(noise)

        dp_confidence = {
            'low': max(0.0, raw_score - ci_half),
            'high': min(1.0, raw_score + ci_half),
            'ciHalfWidth': round(ci_half, 4),
        }

    final_score = raw_score + dp_noise

    # 第二层防护: 截断下界0, 上界=min(1.0, raw_score+0.35)
    # 防止噪声将药物推升超过原始信号3.5倍 (如raw=0.2→最多到0.55)
    # 上界截断是公开函数(仅依赖raw_score和常数), DP后处理定理允许
    ceiling = min(1.0, raw_score + 0.35)
    final_score = max(0.0, min(ceiling, final_score))

    # dp_anomaly用于UI显示: 标记噪声是否显著改变了排序方向
    dp_anomaly = False
    if abs(dp_noise) > 0:
        # 噪声将低分推到高分(可能误导) 或 将高分推到低分(可能埋没好药)
        if (raw_score <= 0.2 and final_score > raw_score + 0.1) or \
           (raw_score >= 0.8 and final_score < raw_score - 0.1):
            dp_anomaly = True

    return final_score, dp_noise, dp_anomaly, dp_confidence


def _translate_recommendation_names(
    recommendations: List[Dict[str, Any]],
    translation_map: Dict[str, str],
) -> None:
    """翻译推荐结果列表中的药物名为中文

    drugName: 替换为中文
    englishName: 保留英文原名
    """
    mapper = get_translation_mapper()
    for rec in recommendations:
        original_name = rec.get('drugName', '')
        if original_name:
            chinese_name = translate_drug_name(original_name, translation_map)
            rec['englishName'] = original_name
            rec['drugName'] = chinese_name

        # 翻译 category (drug_class_en)
        category = rec.get('category', '')
        if category:
            rec['category'] = mapper.translate_class(category)

        # 翻译 safetyType 枚举
        safety_type = rec.get('safetyType', '')
        if safety_type:
            rec['safetyType'] = mapper.translate_enum(safety_type)

        # 翻译 qualityWarning 枚举
        quality_warning = rec.get('qualityWarning', '')
        if quality_warning:
            rec['qualityWarning'] = mapper.translate_enum(quality_warning)

        # 翻译 matchedDisease
        matched_disease = rec.get('matchedDisease', '')
        if matched_disease:
            rec['matchedDisease'] = mapper.translate_condition(matched_disease)

        # 翻译 explanation 中的 matchedDisease
        explanation = rec.get('explanation', {})
        if isinstance(explanation, dict):
            ind_detail = explanation.get('indicationDetail', {})
            if isinstance(ind_detail, dict):
                md = ind_detail.get('matchedDisease', '')
                if md:
                    ind_detail['matchedDisease'] = mapper.translate_condition(md)
                matched_ind = ind_detail.get('matchedIndication', '')
                if matched_ind:
                    ind_detail['matchedIndication'] = mapper.translate_condition(matched_ind)

                # 翻译 matchedConditions 列表
                matched_conditions = ind_detail.get('matchedConditions', [])
                if isinstance(matched_conditions, list):
                    ind_detail['matchedConditions'] = [
                        mapper.translate_condition(c) if isinstance(c, str) else c
                        for c in matched_conditions
                    ]

        # 翻译 warnings 列表中的英文药物名/病况名
        warnings = rec.get('warnings', [])
        if warnings:
            rec['warnings'] = _translate_warnings(warnings)

        # 翻译 explanation.warnings 列表
        explanation_warnings = rec.get('explanation', {}).get('warnings', [])
        if explanation_warnings:
            rec['explanation']['warnings'] = _translate_warnings(explanation_warnings)


def _translate_excluded_drug_names(
    excluded_drugs: List[Dict[str, Any]],
    translation_map: Dict[str, str],
) -> None:
    """翻译排除药物列表中的药物名、类别和排除原因"""
    import re
    mapper = get_translation_mapper()
    for drug in excluded_drugs:
        original_name = drug.get('drug_name', drug.get('drugName', drug.get('name', '')))
        if original_name:
            chinese_name = translate_drug_name(original_name, translation_map)
            drug['englishName'] = original_name
            # 前端期望 camelCase 'drugName'，确保始终存在此键
            drug['drugName'] = chinese_name
            if 'drug_name' in drug:
                drug['drug_name'] = chinese_name
            if 'name' in drug:
                drug['name'] = chinese_name

        # 从 drug_data 提取 category（前端期望此字段）
        drug_data = drug.get('drug_data', {})
        if drug_data and not drug.get('category'):
            drug_class = drug_data.get('drug_class_en', drug_data.get('category', ''))
            if drug_class:
                drug['category'] = mapper.translate_class(drug_class)
        # 翻译已有的 category
        elif drug.get('category'):
            drug['category'] = mapper.translate_class(drug['category'])

        # 前端期望 excludedReason 字段（映射 reason）
        if drug.get('reason') and not drug.get('excludedReason'):
            drug['excludedReason'] = drug['reason']

        # 翻译排除原因中的英文病况名/药物名
        reason = drug.get('reason', '')
        if reason and any(c.isalpha() and ord(c) < 128 for c in reason):
            # reason 含英文内容，逐词替换可翻译的关键词
            translated_reason = reason
            if ': ' in reason:
                prefix, content = reason.split(': ', 1)
                # 1) 先尝试整句翻译（如 "moderate to severe hypertension"）
                full_zh = mapper.translate_condition(content.lower())
                if full_zh != content.lower():
                    translated_reason = f"{prefix}: {full_zh}"
                else:
                    # 2) 逐词扫描替换：condition名、药物名、药物类别名
                    translated_content = content
                    # 按词长降序扫描，避免短词误截长词
                    known_conditions = sorted(
                        (k for k in mapper._condition_map if k in content.lower()),
                        key=len, reverse=True,
                    )
                    for cond_en in known_conditions:
                        cond_zh = mapper._condition_map[cond_en]
                        # 大小写不敏感替换
                        translated_content = re.sub(
                            re.escape(cond_en), cond_zh, translated_content,
                            flags=re.IGNORECASE,
                        )
                    # 替换药物名（使用词边界防止部分替换）
                    for en_name, cn_name in translation_map.items():
                        pattern = r'\b' + re.escape(en_name) + r'\b'
                        try:
                            translated_content = re.sub(
                                pattern, cn_name, translated_content,
                                flags=re.IGNORECASE,
                            )
                        except re.error:
                            pass
                    # 替换药物类别名
                    for cls_en, cls_zh in mapper._class_map.items():
                        # 使用词边界防止部分替换（如 "ARB" 不应匹配 "carbapenems"）
                        pattern = r'\b' + re.escape(cls_en) + r'\b'
                        try:
                            translated_content = re.sub(
                                pattern, cls_zh, translated_content,
                                flags=re.IGNORECASE,
                            )
                        except re.error:
                            pass
                    # 常见描述性词汇替换（使用词边界防止部分替换）
                    desc_map = {
                        'hypersensitivity': '超敏反应',
                        'uncontrolled': '未控制',
                        'contraindicated': '禁忌',
                        'contraindication': '禁忌症',
                        'severe': '重度',
                        'moderate': '中度',
                        'mild': '轻度',
                        'immediate': '速发',
                        'confirmed': '已确诊',
                        'wild-type': '野生型',
                        'or': '或',
                        'to': '至',
                        'with': '伴有',
                        'patients': '患者',
                        'should not': '不应',
                        'avoid': '避免',
                        'history of': '既往',
                        # 常见药物类别名（按长度降序排列，优先匹配长词）
                        'beta-lactamase inhibitors': 'β-内酰胺酶抑制剂',
                        'beta-lactamase inhibitor': 'β-内酰胺酶抑制剂',
                        'carbapenems': '碳青霉烯类',
                        'carbapenem': '碳青霉烯类',
                        'penicillins': '青霉素类',
                        'penicillin': '青霉素',
                        'cephalosporins': '头孢菌素类',
                        'cephalosporin': '头孢菌素',
                        'sulfonylureas': '磺酰脲类',
                        'sulbactam': '舒巴坦',
                        'tazobactam': '他唑巴坦',
                        'clavulanate': '克拉维酸',
                        'insulin': '胰岛素',
                        'metformin': '二甲双胍',
                        'aspirin': '阿司匹林',
                        'warfarin': '华法林',
                        'heparin': '肝素',
                        # 常见病况术语
                        'melanoma': '黑色素瘤',
                        'pulmonary hypertension': '肺动脉高压',
                        'endocrine neoplasia': '内分泌肿瘤',
                        'milk protein': '乳蛋白',
                        'supine': '卧位',
                        'syndrome': '综合征',
                        'peripheral neuropathy': '外周神经病变',
                        'impaired circulation': '循环障碍',
                        'beta-lactams': 'β-内酰胺类',
                        'beta-lactam': 'β-内酰胺类',
                        'other': '其他',
                        'anaphylaxis': '过敏性休克',
                        'e.g.': '例如',
                    }
                    for en_desc, zh_desc in desc_map.items():
                        # 短词（≤3字符）必须使用词边界，防止 "in" 替换 "penicillins"
                        if len(en_desc) <= 3:
                            pattern = r'\b' + re.escape(en_desc) + r'\b'
                        else:
                            pattern = re.escape(en_desc)
                        translated_content = re.sub(
                            pattern, zh_desc, translated_content,
                            flags=re.IGNORECASE,
                        )
                    translated_reason = f"{prefix}: {translated_content}"
            drug['reason'] = translated_reason


def _translate_ddi_warnings(
    ddi_warnings: List[Dict[str, str]],
    translation_map: Dict[str, str],
) -> None:
    """翻译DDI交叉检查警告中的药物名"""
    for warning in ddi_warnings:
        for key in ('drug_a', 'drug_b'):
            original = warning.get(key, '')
            if original:
                chinese_name = translate_drug_name(original, translation_map)
                warning[f'{key}_en'] = original
                warning[key] = chinese_name


def _translate_warnings(warnings: List[str]) -> List[str]:
    """翻译警告列表中的英文药物名/病况名为中文

    警告格式通常是"中文前缀: 英文名"或"中文前缀: 英文名 + 英文名"
    仅翻译其中的英文名部分，保留中文前缀不变。
    """
    mapper = get_translation_mapper()
    translated = []
    for warning in warnings:
        # 警告可能包含已翻译的药物名(来自翻译后的drugName)，
        # 也可能包含英文病况名(来自RuleMarker原始生成)
        # 简化处理: 尝试翻译warning中可能出现的英文病况名
        translated_warning = warning
        # 翻译安全数据未验证警告中的药物名
        if '安全数据未验证' in warning:
            # 格式: "安全数据未验证: EnglishDrugName"
            parts = warning.split(': ', 1)
            if len(parts) == 2:
                drug_en = parts[1]
                drug_zh = translate_drug_name(drug_en, mapper._drug_name_map) if mapper._drug_name_map else drug_en
                translated_warning = f"{parts[0]}: {drug_zh}"
        # 翻译交互警告中的药物名
        elif '交互' in warning or '中度交互' in warning or '严重交互' in warning:
            parts = warning.split(': ', 1)
            if len(parts) == 2:
                # 交互警告可能包含多个药物名用 " + " 连接
                drug_parts = parts[1].split(' + ')
                translated_drug_parts = [
                    translate_drug_name(p.strip(), mapper._drug_name_map) if mapper._drug_name_map else p.strip()
                    for p in drug_parts
                ]
                translated_warning = f"{parts[0]}: {' + '.join(translated_drug_parts)}"
        # 翻译禁忌警告中的病况名
        elif '相对禁忌' in warning or '绝对禁忌' in warning:
            parts = warning.split(': ', 1)
            if len(parts) == 2:
                condition_en = parts[1]
                condition_zh = mapper.translate_condition(condition_en)
                translated_warning = f"{parts[0]}: {condition_zh}"
        translated.append(translated_warning)
    return translated


def _translate_side_effects(drug: Dict[str, Any]) -> List[str]:
    """翻译副作用为中文列表

    优先使用 pipeline_data.json 的 side_effects_raw（英文），
    通过翻译映射器翻译为中文关键词列表。
    如果 side_effects_raw 为空, 回退到 side_effects 字段。
    """
    mapper = get_translation_mapper()

    # 优先从 side_effects_raw 翻译
    raw = drug.get('side_effects_raw', '')
    if raw:
        return mapper.translate_side_effects_raw(raw)

    # 回退到原始 side_effects 列表
    return drug.get('side_effects', [])


class RecommendationPredictor:
    """药物推荐预测器 — 三层架构"""

    def __init__(self):
        self.model: Optional[DeepFM] = None
        self.field_dims: Optional[List[int]] = None
        self.encoder: Optional[FeatureEncoder] = None
        self.drugs_data: List[Dict[str, Any]] = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 三层架构组件
        self.safety_filter = SafetyFilter()
        self.rule_marker = RuleMarker()

        # 安全数据映射
        self.contraindication_map: Dict[str, List[Dict[str, Any]]] = {}
        self.interaction_map: Dict[str, List[Dict[str, Any]]] = {}
        self.critical_interactions: Set[Tuple[str, str]] = set()

        # 药物名英→中翻译映射
        self._drug_name_translation_map: Dict[str, str] = {}

    def load_model(self, model_path: str, field_dims: List[int]) -> None:
        """加载预训练模型"""
        try:
            self.field_dims = field_dims
            self.model = DeepFM(field_dims)
            state_dict = torch.load(model_path, map_location=self.device, weights_only=True)
            # Strip _module. prefix from Opacus/DP-trained checkpoints
            if any(k.startswith('_module.') for k in state_dict):
                state_dict = {k.removeprefix('_module.'): v for k, v in state_dict.items()}
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Model loaded from {model_path}")
        except FileNotFoundError as e:
            raise ModelNotLoadedError(f"Model file not found: {model_path}") from e
        except Exception as e:
            raise ModelNotLoadedError(f"Failed to load model: {e}") from e

    def load_encoder(self, encoder_path: str) -> None:
        """加载特征编码器"""
        self.encoder = FeatureEncoder.load(encoder_path)
        logger.info(f"Encoder loaded from {encoder_path}")

    def init_model(self, field_dims: List[int]) -> None:
        """初始化新模型（用于训练）"""
        self.field_dims = field_dims
        self.model = DeepFM(field_dims)
        self.model.to(self.device)
        logger.info(f"Model initialized with field_dims: {field_dims}")

    def set_drugs_data(self, drugs: List[Dict[str, Any]]) -> None:
        """设置药物数据，合并适应症（保留pipeline_data中的英文结构化数据）

        当后端传入的数据覆盖已有药物时，保留已有的英文结构化字段，
        因为后端DB数据可能缺少 side_effects_raw、drug_class_en 等字段。

        如果传入空列表且已有pipeline_data药品，则跳过（保留现有药品不被清空）。
        """
        if not isinstance(drugs, list):
            logger.warning(f"Invalid drugs_data type: {type(drugs)}, expected list")
            self.drugs_data = []
            return

        # 保护：空列表不应清空已有药品（pipeline_data.json已有1815药品）
        if not drugs and self.drugs_data:
            logger.info(
                f"Empty drugs list received, keeping existing {len(self.drugs_data)} "
                f"pipeline_data drugs (skip override)"
            )
            # 确保翻译缓存已构建（如果之前未构建）
            if not self._drug_name_translation_map:
                self._drug_name_translation_map = build_translation_cache(self.drugs_data)
                logger.info(
                    f"Translation cache built from existing drugs: "
                    f"{len(self._drug_name_translation_map)} entries"
                )
            return

        # 合并逻辑：
        # - 已有药品(self.drugs_data)：保留pipeline_data字段优先，补充MySQL缺失字段
        # - 新传入的药品(不在已有列表中)：直接添加
        existing_drug_map = {
            d.get('generic_name', d.get('name', '')): d
            for d in self.drugs_data
            if d.get('generic_name') or d.get('name')
        }

        # 需要优先保留 pipeline_data 值的字段列表
        PRESERVE_FIELDS = (
            'indications', 'indications_raw', 'side_effects_raw',
            'drug_class_en', 'pregnancy_category', 'typical_dosage',
            'typical_frequency', 'dosage_form', 'strength',
            'route_of_administration', 'availability',
        )

        for drug in drugs:
            name = drug.get('generic_name', drug.get('name', ''))
            existing = existing_drug_map.get(name)
            if existing:
                # 已有药品：pipeline_data字段优先，MySQL补充缺失字段
                for field in PRESERVE_FIELDS:
                    existing_val = existing.get(field)
                    new_val = drug.get(field)
                    if existing_val and not new_val:
                        drug[field] = existing_val
                    elif existing_val and new_val:
                        drug[field] = existing_val
                # MySQL数据中有pipeline_data没有的字段 → 补充进去
                for key, val in drug.items():
                    if key not in existing or not existing[key]:
                        existing[key] = val
            # 不在已有列表中的药品：直接加入map（后端新增药品）

        # 将传入药品中不在已有列表中的添加到map
        for drug in drugs:
            name = drug.get('generic_name', drug.get('name', ''))
            if name not in existing_drug_map:
                existing_drug_map[name] = drug

        # 更新 self.drugs_data 为合并后的完整列表
        self.drugs_data = list(existing_drug_map.values())
        logger.info(f"Drugs data updated: {len(drugs)} drugs")

        # 构建药物名翻译缓存（基于合并后的完整药品列表）
        try:
            self._drug_name_translation_map = build_translation_cache(self.drugs_data)
            translated_count = sum(
                1 for k, v in self._drug_name_translation_map.items() if k != v
            )
            logger.info(
                f"Drug name translation: {translated_count}/{len(self._drug_name_translation_map)} names translated to Chinese"
            )
        except Exception as e:
            logger.warning(f"Failed to build drug translation cache: {e}", exc_info=True)

    def set_safety_data(
        self,
        contraindication_map: Dict[str, List[Dict[str, Any]]],
        interaction_map: Dict[str, List[Dict[str, Any]]],
        critical_interactions: Set[Tuple[str, str]] = None,
    ) -> None:
        """设置安全过滤数据"""
        self.contraindication_map = contraindication_map
        self.interaction_map = interaction_map
        if critical_interactions:
            self.critical_interactions = critical_interactions
        logger.info(
            f"Safety data: {len(contraindication_map)} drugs with contraindications, "
            f"{len(interaction_map)} drugs with interactions, "
            f"{len(self.critical_interactions)} critical interaction pairs"
        )

    def predict(
        self,
        patient_data: Dict[str, Any],
        top_k: int = 4,
        dp_config: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行药物推荐预测 — 三层架构

        Layer 1: SafetyFilter → 确定性硬排除
        Layer 2: RuleMarker → 规则标记（附加警告）
        Layer 3: DeepFM排序 → 个性化排序 + DP噪声

        Args:
            patient_data: 患者数据
            top_k: 返回前k个推荐
            dp_config: DP配置（含enabled, epsilon, delta, noiseMechanism等）
            user_id: 用户标识（用于隐私预算追踪，为None时使用默认追踪器）
        """
        if not self.drugs_data:
            raise DataNotFoundError("No drug data loaded", resource="drugs_data")

        # DP参数校验
        if dp_config and dp_config.get('enabled', False):
            epsilon = dp_config.get('epsilon', 1.0)
            if epsilon <= 0:
                raise PrivacyConfigError(f"Invalid epsilon: {epsilon}, must be > 0")

            # 隐私预算检查: 推理前检查剩余预算
            tracker_user = user_id or 'default'
            tracker = get_budget_tracker(tracker_user)
            can_spend, budget_status = tracker.can_spend(epsilon)
            if not can_spend:
                from app.exceptions import PrivacyBudgetExceededError
                raise PrivacyBudgetExceededError(
                    f"Privacy budget exceeded for user={tracker_user}: "
                    f"ε_spent={budget_status.epsilon_spent_cumulative:.4f} "
                    f"+ ε_query={epsilon:.4f} > ε_budget={budget_status.epsilon_total_budget:.4f}",
                    epsilon_spent=budget_status.epsilon_spent_cumulative,
                    epsilon_budget=budget_status.epsilon_total_budget,
                )

        try:
            # ===== Layer 1: SafetyFilter — 确定性硬排除 =====
            exclusion_result = self.safety_filter.filter(
                patient_data, self.drugs_data,
                self.contraindication_map, self.interaction_map,
                self.critical_interactions,
            )

            # ===== Layer 2: RuleMarker — 规则标记 =====
            flag_result = self.rule_marker.mark(
                patient_data, exclusion_result.safe_candidates,
                self.contraindication_map, self.interaction_map,
            )

            # 统计安全数据未验证的候选药物数量
            unverified_count = sum(
                1 for flags in flag_result.candidate_flags.values()
                if flags.get('contraindication_type') == 'data_unverified'
            )

            # Compute drug-class filter from KnowledgeRouter
            from app.utils.disease_mapper import get_appropriate_drug_classes, get_disease_routing_info
            patient_diseases_cn = patient_data.get('primary_input_diseases',
                                  patient_data.get('original_mapped_diseases',
                                  patient_data.get('diseases', [])))
            if patient_diseases_cn:
                diseases_list = [str(d) for d in patient_diseases_cn if d and d != '__unknown__']
                self._drug_class_filter = get_appropriate_drug_classes(diseases_list)
                # Determine etiology for viral-disease antibiotic penalty
                self._current_route_info = None
                for disease in diseases_list:
                    route_info = get_disease_routing_info(disease)
                    if route_info and route_info.get('etiology') == 'viral':
                        self._current_route_info = route_info
                        break
            else:
                self._drug_class_filter = set()
                self._current_route_info = None

            # ===== Layer 3: DeepFM排序 =====
            ranked_results = self._rank_candidates(
                patient_data, exclusion_result.safe_candidates,
                dp_config,
            )

            # 合并排序结果 + 安全标记
            final_results = self._merge_rank_and_flags(
                ranked_results, flag_result,
            )

            # ===== 规则兜底增强: 有适应症匹配的药物权重提升 =====
            # 必须在取top_k之前执行，确保低分匹配药物不被截掉
            for rec in final_results:
                if rec.get('matchedDisease') and rec.get('matchedDisease') != '未知':
                    rec['score'] = round(min(1.0, rec['score'] * 1.3), 3)

            # ===== 丢失疾病优先提升 =====
            # 当患者真实疾病被vocab代理替代时，匹配真实疾病的药物必须优先于仅匹配代理疾病的药物
            # 否则模型编码偏差会导致代理疾病相关药物（如PPI）压倒真实疾病药物（如泻药）
            vocab_diseases = set(
                str(d).lower() for d in patient_data.get('diseases', []) or []
                if d and d != '__unknown__'
            )
            primary_input = set(
                str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                if d and d != '__unknown__'
            )
            # lost_diseases: 患者实际输入的疾病中，不在vocab中的部分
            lost_diseases = primary_input - vocab_diseases
            if not primary_input:
                original_diseases = set(
                    str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                    if d and d != '__unknown__'
                )
                lost_diseases = original_diseases - vocab_diseases

            # 获取患者用于适应症匹配的完整条件集合（含同义词链）
            indication_conds = set()
            for d in patient_data.get('indication_match_conditions', []) or []:
                if d and d != '__unknown__':
                    indication_conds.add(str(d).lower())

            # 扩展lost_diseases: indication_conds中不在vocab的也视为"真实疾病"
            for cond in indication_conds:
                if cond not in vocab_diseases and cond not in lost_diseases:
                    lost_diseases.add(cond)

            has_lost_diseases = len(lost_diseases) > 0
            if has_lost_diseases:
                logger.info(f"[LOST_DISEASES] lost_diseases={lost_diseases}, primary={primary_input}, vocab={vocab_diseases}, indication_conds={indication_conds}")
                boosted_drugs = []
                penalized_drugs = []
                for rec in final_results:
                    drug_name = rec.get('englishName', rec.get('drugName', ''))
                    drug_data = None
                    for d in self.drugs_data:
                        dn = d.get('generic_name', d.get('name', ''))
                        if dn == drug_name or dn.lower() == drug_name.lower():
                            drug_data = d
                            break
                    if not drug_data:
                        continue
                    # 检查药物是否匹配了患者真实疾病（含indication_conds同义词链）
                    matches_real = False
                    for ind in drug_data.get('indications', []) or []:
                        ind_str = str(ind.get('condition', ind) if isinstance(ind, dict) else ind).lower()
                        if match_indication(indication_conds, ind_str):
                            matches_real = True
                            break
                    if matches_real:
                        old_score = rec['score']
                        rec['score'] = 1.0
                        boosted_drugs.append(f"{drug_name}: {old_score}->1.0")
                    elif rec['score'] > 0.3:
                        # 不匹配任何真实疾病的高分药物=模型偏差，大幅降权
                        old_score = rec['score']
                        rec['score'] = old_score * 0.15
                        penalized_drugs.append(f"{drug_name}: {old_score:.3f}->{rec['score']:.3f}")
                logger.info(f"[LOST_DISEASES] boosted {len(boosted_drugs)} drugs: {boosted_drugs[:10]}")
                if penalized_drugs:
                    logger.info(f"[LOST_DISEASES] penalized {len(penalized_drugs)} drugs: {penalized_drugs[:10]}")

            # ===== 多疾病覆盖优先排序 =====
            # DeepSeek验证发现: 原排序偏向单一疾病(通常高血压), 多病患者的推荐无法覆盖所有疾病
            # 策略: 先为每个疾病选一个最佳匹配药物, 再用最高分药物填充剩余位置
            top_recommendations = self._select_disease_balanced(
                final_results, patient_data, top_k,
            )

            # ===== 跨候选药物 DDI 交叉检查 =====
            # 仅标记警告信息供前端展示，不修改评分
            # 理由: 患者实际只会选用一种药物，不应因"A和B不能联用"而同时惩罚两者
            ddi_warnings: List[Dict[str, str]] = []
            candidate_names = [r.get('drugName', '') for r in top_recommendations]
            if len(candidate_names) >= 2:
                ddi_warnings = check_cross_candidate_ddi(candidate_names)
                conflict_drugs: Set[str] = set()
                for ddi in ddi_warnings:
                    conflict_drugs.add(ddi['drug_a'])
                    conflict_drugs.add(ddi['drug_b'])

                for rec in top_recommendations:
                    name = rec.get('drugName', '')
                    if name in conflict_drugs:
                        rec['crossDdiWarning'] = True
                        pairs = [d for d in ddi_warnings
                                 if d['drug_a'] == name or d['drug_b'] == name]
                        rec['crossDdiDetails'] = pairs

            # ===== 排序质量门控 =====
            MIN_RELIABLE_SCORE = 0.3
            MIN_SEPARATION = 0.15
            quality_warning: Optional[str] = None

            if top_recommendations:
                scores = [r.get('score', 0) for r in top_recommendations]
                max_score = max(scores)
                # 检查是否有适应症匹配药物 — 有适应症匹配时即使模型分低也不清空
                has_matched = any(
                    r.get('matchedDisease') and r.get('matchedDisease') != '未知'
                    for r in top_recommendations
                )
                if max_score < MIN_RELIABLE_SCORE and not has_matched:
                    quality_warning = "NO_RELIABLE_RECOMMENDATION"
                    top_recommendations = []
                elif max_score < MIN_RELIABLE_SCORE and has_matched:
                    quality_warning = "LOW_CONFIDENCE"  # 有适应症但模型分低
                else:
                    # 计算 positive/negative 分数均值（使用 rawScore 避免噪声干扰）
                    pos_scores = [r.get('rawScore', 0) for r in final_results
                                  if r.get('rawScore', 0) >= 0.5]
                    neg_scores = [r.get('rawScore', 0) for r in final_results
                                  if r.get('rawScore', 0) < 0.5]
                    if pos_scores and neg_scores:
                        separation = sum(pos_scores) / len(pos_scores) - sum(neg_scores) / len(neg_scores)
                        if separation < MIN_SEPARATION:
                            quality_warning = "LOW_CONFIDENCE"

            # 检测 DP 置信区间重叠 → uncertainRanking 标记
            dp_confidence_map: Dict[str, Optional[Dict[str, Any]]] = {}
            if dp_config and dp_config.get('enabled', False):
                for rec in top_recommendations:
                    dp_confidence_map[rec.get('drugName', '')] = rec.get('dpConfidence')

                # 两两比较置信区间是否重叠
                for i in range(len(top_recommendations)):
                    for j in range(i + 1, len(top_recommendations)):
                        ci_a = dp_confidence_map.get(top_recommendations[i].get('drugName', ''))
                        ci_b = dp_confidence_map.get(top_recommendations[j].get('drugName', ''))
                        if ci_a and ci_b:
                            # 重叠条件: a.high >= b.low AND b.high >= a.low
                            if ci_a['high'] >= ci_b['low'] and ci_b['high'] >= ci_a['low']:
                                top_recommendations[i]['uncertainRanking'] = True
                                top_recommendations[j]['uncertainRanking'] = True

            # 构建无DP对比版本（用于隐私可视化）
            base_results = self._rank_candidates(
                patient_data, exclusion_result.safe_candidates,
                dp_config=None,  # 无DP噪声
            )
            base_merged = self._merge_rank_and_flags(
                base_results, flag_result,
            )

            # 记录隐私预算消耗
            budget_info = None
            if dp_config and dp_config.get('enabled', False):
                tracker_user = user_id or 'default'
                tracker = get_budget_tracker(tracker_user)
                mechanism = dp_config.get('noiseMechanism', 'laplace')
                delta_spent = dp_config.get('delta', 1e-5) if mechanism == 'gaussian' else 0.0
                budget_status = tracker.spend(
                    epsilon=dp_config.get('epsilon', 1.0),
                    delta=delta_spent,
                    mechanism=mechanism,
                )
                budget_info = {
                    'epsilonSpent': round(budget_status.epsilon_spent_cumulative, 6),
                    'epsilonBudget': budget_status.epsilon_total_budget,
                    'deltaSpent': budget_status.delta_spent_cumulative,
                    'deltaBudget': budget_status.delta_total_budget,
                    'warningLevel': budget_status.warning_level.value,
                    'remainingRatio': round(budget_status.remaining_budget_ratio, 4),
                    'queryCount': budget_status.query_count,
                }

            # 审计日志 — 生成唯一请求ID（无条件，与API响应统一）
            request_id = uuid.uuid4().hex[:12]
            try:
                from app.utils.audit_logger import get_audit_logger, build_patient_summary
                audit = get_audit_logger()
                audit.log_prediction(
                    request_id=request_id,
                    user_id=user_id,
                    patient_summary=build_patient_summary(patient_data),
                    dp_config=dp_config,
                    excluded_drugs=exclusion_result.excluded_drugs,
                    recommended_drugs=top_recommendations,
                    budget_info=budget_info,
                    total_candidates=len(self.drugs_data),
                    total_excluded=len(exclusion_result.excluded_drugs),
                    total_safe=len(exclusion_result.safe_candidates),
                )
            except Exception:
                logger.warning("Audit logging failed (non-blocking)", exc_info=True)

            # 翻译药物名为中文（保留英文原名到 englishName）
            _translate_recommendation_names(top_recommendations, self._drug_name_translation_map)
            _translate_recommendation_names(base_merged[:top_k], self._drug_name_translation_map)
            _translate_excluded_drug_names(exclusion_result.excluded_drugs, self._drug_name_translation_map)
            _translate_ddi_warnings(ddi_warnings, self._drug_name_translation_map)

            return {
                'recommendationId': request_id,
                'requestId': request_id,
                'selected': top_recommendations,
                'base': base_merged[:top_k],
                'dp': top_recommendations,
                'dpEnabled': dp_config.get('enabled', True) if dp_config else False,
                'excludedDrugs': exclusion_result.excluded_drugs,
                'safetyFlags': flag_result.candidate_flags,
                'inferredDiseases': list(patient_data.get('diseases', [])),
                'allDiseases': list(patient_data.get('diseases', []))
                              + list(patient_data.get('chronic_diseases', [])),
                'totalCandidates': len(self.drugs_data),
                'totalExcluded': len(exclusion_result.excluded_drugs),
                'totalSafe': len(exclusion_result.safe_candidates),
                'unverifiedCount': unverified_count,
                'privacyBudget': budget_info,
                'disclaimer': "AI推荐仅供参考，最终用药决策应由临床医师做出",
                'recommendationMode': 'dp_protected' if (dp_config and dp_config.get('enabled', False)) else 'standard',
                'qualityWarning': quality_warning,
                'crossDdiWarnings': ddi_warnings,
            }

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise PredictionError(f"Prediction failed: {e}") from e

    def _rank_candidates(
        self,
        patient_data: Dict[str, Any],
        safe_candidates: List[Dict[str, Any]],
        dp_config: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """对安全候选药物进行排序（Layer 3）

        如果模型已加载：使用DeepFM真实推理
        如果模型未加载：使用基于规则的评分（降级模式，标注"演示模式"）
        """
        if self.model is not None and self.encoder is not None:
            return self._model_rank(patient_data, safe_candidates, dp_config)
        else:
            return self._rule_rank(patient_data, safe_candidates, dp_config)

    def _model_rank(
        self,
        patient_data: Dict[str, Any],
        safe_candidates: List[Dict[str, Any]],
        dp_config: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """DeepFM模型真实推理排序"""
        results: List[Dict[str, Any]] = []

        # 提取患者疾病条件用于适应症匹配检查
        # 优先使用 indication_match_conditions（包含所有映射结果，不受vocab过滤）
        # fallback 到 diseases（vocab过滤后的词）
        patient_conditions = set()
        for d in patient_data.get('indication_match_conditions', []) or []:
            if d and d != '__unknown__':
                patient_conditions.add(str(d).lower())
        if not patient_conditions:
            for d in patient_data.get('diseases', []) or []:
                if d and d != '__unknown__':
                    patient_conditions.add(str(d).lower())
        for d in patient_data.get('chronic_diseases', []) or []:
            if d and d != '__unknown__':
                patient_conditions.add(str(d).lower())
        logger.info(f"[PATIENT_CONDITIONS] conditions={patient_conditions}, diseases={patient_data.get('diseases', [])}, indication_match={patient_data.get('indication_match_conditions', [])}")

        # 识别"丢失疾病"：患者实际疾病中被vocab过滤掉的部分
        # 这些疾病在模型编码中由vocab代理词替代，导致模型排序偏向代理疾病相关药物
        # 匹配丢失疾病适应症的药物需要额外boost以弥补模型编码偏差
        vocab_diseases = set(
            str(d).lower() for d in patient_data.get('diseases', []) or []
            if d and d != '__unknown__'
        )
        primary_input_diseases = set(
            str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
            if d and d != '__unknown__'
        )
        original_diseases = set(
            str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
            if d and d != '__unknown__'
        )
        # lost_diseases: 真实疾病中被vocab过滤掉的
        # 使用primary_input_diseases(不含扩展同义词)精确计算
        lost_diseases = primary_input_diseases - vocab_diseases if primary_input_diseases else original_diseases - vocab_diseases
        # 扩展lost_diseases: 包含indication_match_conditions中不在vocab的疾病
        # 这确保diarrhea/nausea/bacterial infections等在同义词链中的词也被视为"真实疾病"
        # 避免"enteritis"→lost_disease但"diarrhea"→vocab_disease导致匹配腹泻的药物不被boost
        for cond in patient_conditions:
            if cond not in vocab_diseases and cond not in lost_diseases:
                lost_diseases.add(cond)
        has_lost_diseases = len(lost_diseases) > 0

        for drug in safe_candidates:
            # 构建特征记录
            record = self._build_record(patient_data, drug)

            # FeatureEncoder 编码
            field_indices, continuous_features = self.encoder.transform(record)

            # DeepFM推理
            field_tensor = torch.tensor(
                field_indices, dtype=torch.long, device=self.device
            ).unsqueeze(0)
            cont_tensor = None
            if continuous_features:
                cont_tensor = torch.tensor(
                    continuous_features, dtype=torch.float, device=self.device
                ).unsqueeze(0)

            with torch.no_grad():
                logits, embeds = self.model(field_tensor, cont_tensor)
            # v3: DeepFM返回raw logits, 推理时手动sigmoid
            prob = torch.sigmoid(logits).item()
            raw_score = prob

            # 检查适应症匹配 — 用于豁免临床阈值
            has_indication = False
            matches_lost_disease = False  # 是否匹配vocab丢失的真实疾病
            drug_indications = drug.get('indications', []) or []
            for ind in drug_indications:
                ind_str = str(ind.get('condition', ind) if isinstance(ind, dict) else ind)
                if match_indication(patient_conditions, ind_str):
                    has_indication = True
                    # 检查是否匹配了"丢失疾病"（患者真实疾病，不在vocab中）
                    if lost_diseases and match_indication(lost_diseases, ind_str):
                        matches_lost_disease = True
                    break

            # 对匹配患者真实疾病的药物施加显著boost
            # patient_conditions包含indication_match_conditions（完整映射结果）
            # has_indication=True意味着药物匹配了患者的真实疾病（含同义词链）
            if has_indication:
                if matches_lost_disease:
                    raw_score = min(1.0, raw_score + 0.5)
                else:
                    # 匹配patient_conditions但不直接匹配lost_disease
                    # 仍需boost，因为模型排序偏向非相关高分药物
                    raw_score = min(1.0, raw_score + 0.4)

            # Drug-class relevance check via KnowledgeRouter
            # Boost drugs from clinically appropriate classes; penalize wrong classes
            drug_class_filter = getattr(self, '_drug_class_filter', None)
            if drug_class_filter:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                drug_gn_lower = drug_name.lower()
                class_match = 0.0
                for target_class in drug_class_filter:
                    target_lower = target_class.lower()
                    if target_lower in drug_class_lower or drug_class_lower in target_lower:
                        class_match = max(class_match, 0.25)
                    if target_lower in drug_gn_lower:
                        class_match = max(class_match, 0.1)
                if class_match > 0:
                    raw_score = min(1.0, raw_score + class_match)

                # Penalize clearly wrong drug classes for viral diseases
                route_info = getattr(self, '_current_route_info', None)
                if route_info and route_info.get('etiology') == 'viral' and class_match == 0:
                    wrong_class_kw = ['antibiotic', 'antibacterial', 'cephalosporin',
                                      'penicillin', 'fluoroquinolone', 'macrolide']
                    if any(kw in drug_class_lower for kw in wrong_class_kw):
                        raw_score *= 0.3

            # 对不匹配任何真实疾病的高分药物施加惩罚
            # 当存在lost_diseases时，模型高分可能来自vocab代理偏差而非临床相关性
            if has_lost_diseases and not has_indication and raw_score > 0.3:
                raw_score *= 0.15  # 大幅降权：高分但无适应症匹配=模型偏差

            # Feedback penalty: learned from doctor rejections
            feedback = get_feedback_learner()
            disease_en = drug.get('matched_disease_en', '')
            if not disease_en:
                # Try to get from patient data
                diseases = patient_data.get('diseases', []) or []
                primary_diseases = patient_data.get('primary_input_diseases', []) or []
                candidate_diseases = primary_diseases or diseases
                if candidate_diseases:
                    disease_en = str(candidate_diseases[0]).lower()

            if disease_en:
                fb_drug_name = drug.get('generic_name', drug.get('name', ''))
                drug_class_en = str(drug.get('drug_class_en', '')).lower()
                penalty = feedback.get_penalty(disease_en, drug_class_en)
                if penalty < 1.0:
                    drug_penalty = feedback.get_drug_penalty(disease_en, fb_drug_name)
                    effective_penalty = min(penalty, drug_penalty)
                    raw_score *= effective_penalty
                    if effective_penalty < 0.8:
                        logger.debug(f"Feedback penalty applied: {fb_drug_name} for {disease_en} = {effective_penalty:.1f}x")

            # DP噪声（仅作用于排序层）
            final_score, dp_noise, dp_anomaly, dp_confidence = _apply_dp_noise(
                raw_score, dp_config, has_indication=has_indication
            )

            drug_name = drug.get('generic_name', drug.get('name', ''))

            # 生成可解释性分析
            explanation = generate_explanation(
                patient_data=patient_data,
                drug=drug,
                raw_score=raw_score,
                mode='model',
                safety_flags=None,  # safety_flags在merge阶段整合
                embeds=embeds.squeeze(0),  # [num_fields, embed_dim]
                field_indices=field_indices,
                encoder=self.encoder,
                contraindication_map=self.contraindication_map,
                interaction_map=self.interaction_map,
            )

            drug_id = hash(drug_name) % 100000  # 稳定唯一ID（基于药物名hash）
            results.append({
                'drugId': drug_id,
                'drugName': drug_name,
                'category': drug.get('category', drug.get('drug_class_en', '')),
                'dosage': drug.get('typical_dosage', drug.get('strength', '')),
                'frequency': drug.get('typical_frequency', ''),
                'confidence': round(min(max(raw_score * 100, 0), 100), 1),
                'score': round(final_score, 3),
                'rawScore': round(raw_score, 3),
                'dpNoise': round(dp_noise, 3) if dp_config and dp_config.get('enabled') else None,
                'dpConfidence': dp_confidence,
                'reason': "基于DeepFM模型推理",
                'interactions': [],
                'sideEffects': _translate_side_effects(drug),
                'matchedDisease': explanation['indicationDetail'].get('matchedDisease'),
                'explanation': explanation,
                'mode': 'model',
                'dpAnomaly': dp_anomaly,
            })

        # 多维度排序: 安全级别 > 适应症匹配 > DP评分 > 原始评分
        # 确保安全药物优先, 防止DP噪声将高风险药物推到首位
        def _safety_priority(rec):
            st = rec.get('safetyType', 'safe')
            if st == 'safe':
                return 3
            if st in ('relative_contraindication',):
                return 2
            if st in ('off_label', 'unverified', 'data_unverified'):
                return 1
            return 0

        results.sort(key=lambda x: (
            _safety_priority(x),
            1 if x.get('matchedDisease') and x.get('matchedDisease') != '未知' else 0,
            x['score'],
            x.get('rawScore', 0),
        ), reverse=True)
        return results

    def _rule_rank(
        self,
        patient_data: Dict[str, Any],
        safe_candidates: List[Dict[str, Any]],
        dp_config: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """基于规则的评分排序（降级模式）

        当模型未加载时使用，明确标注为"演示模式"
        不伪装百分比置信度
        """
        results: List[Dict[str, Any]] = []

        # 收集患者疾病
        patient_conditions = set()
        # 优先使用 indication_match_conditions（包含所有映射结果，不受vocab过滤）
        for d in patient_data.get('indication_match_conditions', []) or []:
            if d and d != '__unknown__':
                patient_conditions.add(str(d).lower())
        if not patient_conditions:
            for d in patient_data.get('diseases', []) or []:
                if d and d != '__unknown__':
                    patient_conditions.add(str(d).lower())
        for d in patient_data.get('chronic_diseases', []) or []:
            if d and d != '__unknown__':
                patient_conditions.add(str(d).lower())

        for drug in safe_candidates:
            drug_name = drug.get('generic_name', drug.get('name', ''))

            # 基于适应症匹配计算基础评分
            base_score = 0.05  # 无适应症 → 低分

            # 检查适应症匹配 (v2: 使用clinical_matcher标准化匹配)
            # 优先匹配结构化 indications，其次匹配 indications_raw
            matched = False
            indications = drug.get('indications', []) or []
            for ind in indications:
                ind_str = str(ind).lower() if isinstance(ind, str) else str(ind.get('condition', '')).lower()
                if match_indication(patient_conditions, ind_str):
                    evidence = ind.get('type', 'On Label') if isinstance(ind, dict) else 'On Label'
                    if evidence.lower() == 'on label':
                        base_score = 1.0
                    else:
                        base_score = max(base_score, 0.7)
                    matched = True
                    break

            # fallback: 匹配 indications_raw（简短英文描述）
            if not matched:
                raw = drug.get('indications_raw', '') or ''
                if raw:
                    # indications_raw 可能用 | 分隔多种适应症
                    raw_parts = [p.strip().lower() for p in raw.split('|')]
                    for part in raw_parts:
                        if part and match_indication(patient_conditions, part):
                            base_score = max(base_score, 0.8)  # raw匹配略低于结构化
                            matched = True
                            break

            # Feedback penalty for rule-based ranking
            feedback = get_feedback_learner()
            disease_en = str(patient_data.get('diseases', [''])[0] if patient_data.get('diseases') else '').lower()
            if disease_en:
                drug_class_en = str(drug.get('drug_class_en', '')).lower()
                penalty = feedback.get_penalty(disease_en, drug_class_en)
                if penalty < 1.0:
                    drug_penalty = feedback.get_drug_penalty(disease_en, drug_name)
                    base_score *= min(penalty, drug_penalty)

            # DP噪声
            final_score, dp_noise, dp_anomaly, dp_confidence = _apply_dp_noise(base_score, dp_config)

            # 生成可解释性分析（演示模式无embeds）
            explanation = generate_explanation(
                patient_data=patient_data,
                drug=drug,
                raw_score=base_score,
                mode='demo',
                safety_flags=None,
                embeds=None,
                field_indices=None,
                encoder=None,
                contraindication_map=self.contraindication_map,
                interaction_map=self.interaction_map,
            )

            drug_id = hash(drug_name) % 100000  # 稳定唯一ID（基于药物名hash）
            results.append({
                'drugId': drug_id,
                'drugName': drug_name,
                'category': drug.get('category', drug.get('drug_class_en', '')),
                'dosage': drug.get('typical_dosage', drug.get('strength', '')),
                'frequency': drug.get('typical_frequency', ''),
                'confidence': None,
                'score': round(final_score, 3),
                'rawScore': round(base_score, 3),
                'dpNoise': round(dp_noise, 3) if dp_config and dp_config.get('enabled') else None,
                'dpConfidence': dp_confidence,
                'reason': "基于规则匹配（演示模式，模型未加载）",
                'interactions': [],
                'sideEffects': _translate_side_effects(drug),
                'matchedDisease': explanation['indicationDetail'].get('matchedDisease'),
                'explanation': explanation,
                'mode': 'demo',
                'dpAnomaly': dp_anomaly,
            })

        # 多维度排序: 安全级别 > 适应症匹配 > DP评分 > 原始评分
        def _safety_priority(rec):
            st = rec.get('safetyType', 'safe')
            if st == 'safe':
                return 3
            if st in ('relative_contraindication',):
                return 2
            if st in ('off_label', 'unverified', 'data_unverified'):
                return 1
            return 0

        results.sort(key=lambda x: (
            _safety_priority(x),
            1 if x.get('matchedDisease') and x.get('matchedDisease') != '未知' else 0,
            x['score'],
            x.get('rawScore', 0),
        ), reverse=True)
        return results

    def _merge_rank_and_flags(
        self,
        ranked_results: List[Dict[str, Any]],
        flag_result: Any,
    ) -> List[Dict[str, Any]]:
        """合并排序结果与安全标记"""
        merged = []
        for rec in ranked_results:
            drug_name = rec.get('drugName', '')
            flags = flag_result.candidate_flags.get(drug_name, {})
            merged_rec = dict(rec)
            merged_rec['warnings'] = flags.get('warnings', [])
            merged_rec['requiresReview'] = flags.get('requires_review', False)
            merged_rec['safetyType'] = flags.get('contraindication_type', 'safe')

            # 将Layer 2警告合并到explanation中（去重）
            explanation = dict(merged_rec.get('explanation', {}))
            existing_warnings = set(explanation.get('warnings', []))
            layer2_warnings = flags.get('warnings', [])
            merged_warnings = list(existing_warnings) + [
                w for w in layer2_warnings if w not in existing_warnings
            ]
            explanation['warnings'] = merged_warnings
            merged_rec['explanation'] = explanation

            merged.append(merged_rec)
        return merged

    def _select_disease_balanced(
        self,
        all_results: List[Dict[str, Any]],
        patient_data: Dict[str, Any],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """多疾病覆盖优先排序选择

        DeepSeek验证发现: 原排序偏向单一疾病(通常高血压),
        多病患者的推荐无法覆盖所有疾病。
        策略:
        1. 识别患者所有疾病
        2. 为每个疾病选一个最佳匹配药物
        3. 用最高分药物填充剩余位置
        4. 如果某疾病无匹配药物, 用该疾病分数最高的药物代替
        """
        # 先按综合评分排序(适应症匹配 > DP评分 > 原始评分)
        all_results.sort(key=lambda x: (
            1 if x.get('matchedDisease') and x.get('matchedDisease') != '未知' else 0,
            x['score'],
            x.get('rawScore', 0),
        ), reverse=True)

        # 收集患者疾病集合（去重：只用primary_input + vocab_diseases，不含扩展同义词）
        # 扩展同义词（如"head pain"="headache"）会导致过多疾病占用top_k位置
        # 真正需要覆盖的是: 患者输入的疾病(primary) + vocab映射的疾病(vocab)
        primary_input_set = set(
            str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
            if d and d != '__unknown__'
        )
        vocab_diseases_set = set(
            str(d).lower() for d in patient_data.get('diseases', []) or []
            if d and d != '__unknown__'
        )
        # 合并: 患者输入的疾病 + vocab疾病（去重）
        patient_diseases: List[str] = sorted(primary_input_set | vocab_diseases_set)

        # lost_diseases: 患者实际输入的疾病中不在vocab中的部分
        lost_diseases = primary_input_set - vocab_diseases_set if primary_input_set else set()
        logger.info(f"[DISEASE_BALANCED] diseases={patient_diseases}, top_k={top_k}, total={len(all_results)}, lost={lost_diseases}, primary={primary_input_set}")

        # 只有1种疾病时, 直接取top_k最高分
        if len(patient_diseases) <= 1:
            return all_results[:top_k]

        # 疾病排序: lost_diseases优先于vocab_diseases
        priority_diseases = []
        other_diseases = []
        for d in patient_diseases:
            if d in lost_diseases:
                priority_diseases.append(d)
            else:
                other_diseases.append(d)
        ordered_diseases = priority_diseases + other_diseases

        # 为每个疾病找最佳匹配药物（按优先级排序）
        # 关键策略: 当lost_diseases存在时，限制vocab代理疾病的位置数
        # vocab代理词(headache/migraine)是lost_disease(cluster headache)的模型编码代理
        # 不应让代理疾病药物(NSAIDs/β-blockers)占据大多数推荐位置
        # 真实疾病药物(Sumatriptan/Ergotamine)应优先占据剩余位置
        selected: List[Dict[str, Any]] = []
        selected_names: Set[str] = set()

        # 先为每个lost_disease选一个最佳药物
        # 优先选择on_label药物（主要治疗），其次选择off_label药物（辅助治疗）
        for disease in priority_diseases:
            if len(selected) >= top_k:
                break
            best_for_disease = None
            best_evidence_level = 'unknown'
            for rec in all_results:
                if rec.get('drugName', '') in selected_names:
                    continue
                if self._drug_matches_disease(rec, disease):
                    # Check evidence level: on_label > off_label > supportive > unknown
                    ev_level = str(rec.get('explanation', {}).get('evidenceLevel', 'unknown')).lower()
                    ev_priority = {'on_label': 3, 'off_label': 2, 'supportive': 1, 'unknown': 0}
                    current_priority = ev_priority.get(ev_level, 0)
                    if best_for_disease is None:
                        best_for_disease = rec
                        best_evidence_level = ev_level
                    elif current_priority > ev_priority.get(best_evidence_level, 0):
                        # Higher evidence level wins regardless of score
                        best_for_disease = rec
                        best_evidence_level = ev_level
                    elif current_priority == ev_priority.get(best_evidence_level, 0) and rec['score'] > best_for_disease['score']:
                        # Same evidence level, compare scores
                        best_for_disease = rec
                        best_evidence_level = ev_level
            if best_for_disease:
                selected.append(best_for_disease)
                selected_names.add(best_for_disease['drugName'])

        # 为vocab疾病选药，但限制数量: 每个lost_disease只给vocab疾病1个位置
        # 避免选择被proxy惩罚的药物(如焦虑代理下的Propranolol)
        vocab_slots = max(1, len(lost_diseases)) if lost_diseases else top_k
        vocab_filled = 0
        for disease in other_diseases:
            if len(selected) >= top_k:
                break
            if vocab_filled >= vocab_slots:
                break  # vocab疾病药物位置已满
            best_for_disease = None
            for rec in all_results:
                if rec.get('drugName', '') in selected_names:
                    continue
                if self._drug_matches_disease(rec, disease):
                    # Skip proxy-penalized drugs (score <= 0.35 indicates proxy penalty)
                    if lost_diseases and rec.get('score', 0) < 0.4:
                        continue
                    if best_for_disease is None or rec['score'] > best_for_disease['score']:
                        best_for_disease = rec
            if best_for_disease:
                selected.append(best_for_disease)
                selected_names.add(best_for_disease['drugName'])
                vocab_filled += 1

        # 填充剩余位置: 优先选择匹配lost_disease的药物，再选其他高分药物
        remaining_slots = top_k - len(selected)
        if remaining_slots > 0:
            # 第一轮: 填充匹配lost_disease的药物（更多治疗选择）
            # 优先选择matchedDisease直接匹配lost_disease的药物（特异性高）
            # 再选择通过indications匹配的药物（特异性较低）
            if lost_diseases:
                lost_matches = []
                # 收集所有匹配lost_disease的候选药物
                lost_candidates = []
                for rec in all_results:
                    if rec.get('drugName', '') in selected_names:
                        continue
                    if self._drug_matches_lost_disease(rec, lost_diseases):
                        # 判断特异性: matchedDisease直接匹配lost_disease → 高特异性
                        # 例: matchedDisease="cluster headache" 匹配 ld="cluster headache" → spec=2
                        # 例: matchedDisease="cluster headache prophylaxis" 包含 ld → spec=1
                        # 例: matchedDisease="headache" 虽包含在ld中但更generic → spec=0
                        specificity = 0
                        matched_disease = str(rec.get('matchedDisease', '')).lower()
                        for ld in lost_diseases:
                            if ld == matched_disease:
                                specificity = 2  # 精确匹配（最高特异性）
                            elif ld in matched_disease and len(ld) >= 4:
                                specificity = max(specificity, 1)  # lost_disease是matchedDisease的子串（高特异性）
                        lost_candidates.append((specificity, rec))

                # 按特异性+证据等级排序: 高特异性优先，on_label优先，同等条件按score排序
                ev_priority = {'on_label': 3, 'off_label': 2, 'supportive': 1, 'unknown': 0}
                lost_candidates.sort(key=lambda x: (
                    -x[0],  # specificity (high first)
                    -ev_priority.get(str(x[1].get('explanation', {}).get('evidenceLevel', 'unknown')).lower(), 0),  # evidence (on_label first)
                    -x[1].get('score', 0),  # score (high first)
                    -x[1].get('rawScore', 0),  # rawScore
                ))

                for specificity, rec in lost_candidates:
                    if remaining_slots <= 0:
                        break
                    selected.append(rec)
                    selected_names.add(rec['drugName'])
                    remaining_slots -= 1
                    lost_matches.append(f"{rec.get('drugName','?')}(spec={specificity},matched={rec.get('matchedDisease','?')})")
                logger.info(f"[LOST_FILL] filled={lost_matches}")

            # 第二轮: 用最高分药物填充剩余位置
            if remaining_slots > 0:
                for rec in all_results:
                    if remaining_slots <= 0:
                        break
                    if rec.get('drugName', '') not in selected_names:
                        selected.append(rec)
                        selected_names.add(rec['drugName'])
                        remaining_slots -= 1

        logger.info(f"[DISEASE_BALANCED] selected={[f'{s.get('drugName','?')}(score={s.get('score')},matched={s.get('matchedDisease','?')})' for s in selected]}")

        return selected[:top_k]

    def _drug_matches_disease(
        self,
        rec: Dict[str, Any],
        disease: str,
    ) -> bool:
        """检查推荐药物是否匹配特定疾病

        检查matchedDisease字段和explanation.indicationDetail中的匹配信息
        """
        matched_disease = rec.get('matchedDisease', '')
        if matched_disease and matched_disease != '未知':
            # 比较标准化后的疾病名
            from app.utils.clinical_matcher import normalize_disease
            if normalize_disease(disease) == normalize_disease(str(matched_disease).lower()):
                return True
            # whole-word匹配(允许"diabetes"匹配"diabetes mellitus"等)
            if disease in str(matched_disease).lower() or str(matched_disease).lower() in disease:
                return True

        # 检查explanation中的匹配适应症列表
        explanation = rec.get('explanation', {})
        if isinstance(explanation, dict):
            ind_detail = explanation.get('indicationDetail', {})
            if isinstance(ind_detail, dict):
                matched_inds = ind_detail.get('matchedIndications', [])
                if isinstance(matched_inds, list):
                    for ind in matched_inds:
                        if isinstance(ind, dict):
                            ind_cond = str(ind.get('condition', '')).lower()
                        else:
                            ind_cond = str(ind).lower()
                        if disease in ind_cond or ind_cond in disease:
                            return True

        return False

    def _drug_matches_lost_disease(
        self,
        rec: Dict[str, Any],
        lost_diseases: Set[str],
    ) -> bool:
        """检查推荐药物是否匹配任意lost_disease"""
        for disease in lost_diseases:
            if self._drug_matches_disease(rec, disease):
                return True
        return False

    def _build_record(
        self, patient_data: Dict[str, Any], drug: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建特征记录（使用共享record_builder）"""
        return build_feature_record(patient_data, drug)


predictor = RecommendationPredictor()