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
from app.utils.privacy_budget import get_budget_tracker, BudgetWarningLevel
from app.utils.clinical_matcher import match_indication
from app.pipeline.record_builder import build_feature_record
from app.services.explanation_generator import generate_explanation
from app.data.critical_interactions import check_cross_candidate_ddi, is_critical_interaction
from app.utils.drug_translator import build_translation_cache, translate_drug_name
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
    CLINICAL_THRESHOLD = 0.15
    if raw_score < CLINICAL_THRESHOLD:
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
    for rec in recommendations:
        original_name = rec.get('drugName', '')
        if original_name:
            chinese_name = translate_drug_name(original_name, translation_map)
            rec['englishName'] = original_name
            rec['drugName'] = chinese_name


def _translate_excluded_drug_names(
    excluded_drugs: List[Dict[str, Any]],
    translation_map: Dict[str, str],
) -> None:
    """翻译排除药物列表中的药物名"""
    for drug in excluded_drugs:
        original_name = drug.get('drug_name', drug.get('drugName', drug.get('name', '')))
        if original_name:
            chinese_name = translate_drug_name(original_name, translation_map)
            drug['englishName'] = original_name
            if 'drug_name' in drug:
                drug['drug_name'] = chinese_name
            if 'drugName' in drug:
                drug['drugName'] = chinese_name
            if 'name' in drug:
                drug['name'] = chinese_name


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
        """设置药物数据，合并适应症（保留pipeline_data中的英文结构化适应症）

        当后端传入的数据覆盖已有药物时，保留已有的英文结构化 indications，
        不被后端的中文 indications 覆盖（后端 indications 是中文且可能为空）。
        """
        if not isinstance(drugs, list):
            logger.warning(f"Invalid drugs_data type: {type(drugs)}, expected list")
            self.drugs_data = []
            return

        # 合并适应症：保留已有的英文结构化 indications
        existing_drug_map = {
            d.get('generic_name', d.get('name', '')): d
            for d in self.drugs_data
            if d.get('generic_name') or d.get('name')
        }

        for drug in drugs:
            name = drug.get('generic_name', drug.get('name', ''))
            existing = existing_drug_map.get(name)
            if existing:
                # 保留已有的英文结构化 indications（来自 pipeline_data.json）
                existing_indications = existing.get('indications', []) or []
                new_indications = drug.get('indications', []) or []

                # 如果已有 indications 是结构化英文（来自DeepSeek），且新 indications 是中文/空，
                # 则保留已有的
                if existing_indications and not new_indications:
                    drug['indications'] = existing_indications
                elif existing_indications and new_indications:
                    # 已有英文结构化优先（更完整），新数据作为补充
                    drug['indications'] = existing_indications
                # 如果已有 indications_raw 但 indications 为空，也保留
                if existing.get('indications_raw') and not drug.get('indications_raw'):
                    drug['indications_raw'] = existing.get('indications_raw')

        self.drugs_data = drugs
        logger.info(f"Drugs data updated: {len(drugs)} drugs")

        # 构建药物名翻译缓存
        try:
            self._drug_name_translation_map = build_translation_cache(drugs)
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

            # ===== Layer 3: DeepFM排序 =====
            ranked_results = self._rank_candidates(
                patient_data, exclusion_result.safe_candidates,
                dp_config,
            )

            # 合并排序结果 + 安全标记
            final_results = self._merge_rank_and_flags(
                ranked_results, flag_result,
            )

            # 取 top_k
            top_recommendations = final_results[:top_k]

            # ===== 跨候选药物 DDI 交叉检查 =====
            ddi_warnings: List[Dict[str, str]] = []
            candidate_names = [r.get('drugName', '') for r in top_recommendations]
            if len(candidate_names) >= 2:
                ddi_warnings = check_cross_candidate_ddi(candidate_names)
                # 降级冲突药物：将存在致命交互的药物 score *= 0.05
                conflict_drugs: Set[str] = set()
                for ddi in ddi_warnings:
                    conflict_drugs.add(ddi['drug_a'])
                    conflict_drugs.add(ddi['drug_b'])

                for rec in top_recommendations:
                    name = rec.get('drugName', '')
                    if name in conflict_drugs:
                        rec['score'] = round(rec.get('score', 0) * 0.05, 3)
                        rec['crossDdiWarning'] = True
                        # 找到与此药物冲突的具体对
                        pairs = [d for d in ddi_warnings
                                 if d['drug_a'] == name or d['drug_b'] == name]
                        rec['crossDdiDetails'] = pairs

                # 重新排序（降级后可能改变排名）
                top_recommendations.sort(key=lambda x: x['score'], reverse=True)

            # ===== 排序质量门控 =====
            MIN_RELIABLE_SCORE = 0.3
            MIN_SEPARATION = 0.15
            quality_warning: Optional[str] = None

            if top_recommendations:
                scores = [r.get('score', 0) for r in top_recommendations]
                max_score = max(scores)
                if max_score < MIN_RELIABLE_SCORE:
                    quality_warning = "NO_RELIABLE_RECOMMENDATION"
                    top_recommendations = []
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

            # DP噪声（仅作用于排序层）
            final_score, dp_noise, dp_anomaly, dp_confidence = _apply_dp_noise(raw_score, dp_config)

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

            results.append({
                'drugId': drug.get('id', 0),
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
                'sideEffects': drug.get('side_effects', []),
                'matchedDisease': explanation['indicationDetail'].get('matchedDisease'),
                'explanation': explanation,
                'mode': 'model',
                'dpAnomaly': dp_anomaly,
            })

        # 按score排序
        results.sort(key=lambda x: x['score'], reverse=True)
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

            results.append({
                'drugId': drug.get('id', 0),
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
                'sideEffects': drug.get('side_effects', []),
                'matchedDisease': explanation['indicationDetail'].get('matchedDisease'),
                'explanation': explanation,
                'mode': 'demo',
                'dpAnomaly': dp_anomaly,
            })

        results.sort(key=lambda x: x['score'], reverse=True)
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

    def _build_record(
        self, patient_data: Dict[str, Any], drug: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建特征记录（使用共享record_builder）"""
        return build_feature_record(patient_data, drug)


predictor = RecommendationPredictor()