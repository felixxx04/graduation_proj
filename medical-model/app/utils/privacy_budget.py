"""差分隐私预算追踪器 — 组合定理 + (ε,δ)完整追踪 + 告警

核心功能:
1. 强组合定理(Strong Composition): k次查询累计ε_comp = √(2k·ln(1/δ_g))·ε + kε²
   注: ln(1/δ_g)而非ln(1.25/δ_g)，1.25系数仅用于Gaussian机制sigma计算
2. (ε,δ)完整追踪: 每次查询记录实际消耗的(ε,δ)对
3. 50%/80%告警: 预算使用达50%时WARNING, 80%时ERROR(可配置)
4. 全局预算上限: 单用户/会话累计ε不超过budget上限

设计原则:
- 预算追踪仅作用于推理层(Layer 3 DeepFM排序), 不影响安全排除层(Layer 1)
- 每次predict()调用消耗一次预算
- 训练时DP-SGD的隐私预算由Opacus PrivacyEngine独立管理, 不在此追踪
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class BudgetWarningLevel(Enum):
    """预算告警等级"""
    OK = "ok"
    WARNING_50 = "warning_50"     # 已用50%预算
    CRITICAL_80 = "critical_80"   # 已用80%预算
    EXCEEDED = "exceeded"          # 预算已耗尽


@dataclass(frozen=True)
class BudgetSpent:
    """单次查询的预算消耗记录"""
    epsilon_spent: float
    delta_spent: float
    mechanism: str          # 'laplace' or 'gaussian'
    timestamp: float
    query_id: Optional[str] = None


@dataclass
class BudgetStatus:
    """当前预算状态快照"""
    epsilon_total_budget: float
    epsilon_spent_cumulative: float     # 组合定理后累计ε
    epsilon_spent_naive: float          # 简单求和ε (对比用)
    delta_total_budget: float
    delta_spent_cumulative: float
    query_count: int
    warning_level: BudgetWarningLevel
    remaining_budget_ratio: float       # 0.0~1.0


class PrivacyBudgetTracker:
    """差分隐私预算追踪器

    使用强组合定理(Strong Composition Theorem)计算累计隐私损失:
    ε_comp = √(2k·ln(1/δ_g))·ε_max + k·ε_max²

    其中:
    - k: 查询次数
    - ε: 每次查询的epsilon
    - δ_g: 全局delta (组合定理自由参数，默认1e-5)
    - 注: ln(1/δ_g)而非ln(1.25/δ_g)，1.25系数仅用于Gaussian机制sigma计算

    对于Laplace机制: δ_single = 0 (纯ε-DP)
    对于Gaussian机制: δ_single = delta参数 (近似(ε,δ)-DP)

    can_spend()使用与get_status()相同的强组合定理预测，
    确保预算检查与实际隐私损失计算一致。

    Args:
        epsilon_budget: 全局ε预算上限 (默认3.0)
        delta_budget: 全局δ预算上限 (默认1e-5)
        warning_threshold: WARNING告警阈值 (默认0.5, 即50%)
        critical_threshold: CRITICAL告警阈值 (默认0.8, 即80%)
    """

    def __init__(
        self,
        epsilon_budget: float = 10.0,  # 强组合定理下需要更大budget，3.0不足以支持eps=1.0的单次查询
        delta_budget: float = 1e-5,
        warning_threshold: float = 0.5,
        critical_threshold: float = 0.8,
    ):
        if epsilon_budget <= 0:
            raise ValueError(f"epsilon_budget must be > 0, got {epsilon_budget}")
        if delta_budget <= 0 or delta_budget >= 1:
            raise ValueError(f"delta_budget must be in (0, 1), got {delta_budget}")
        if not (0 < warning_threshold < critical_threshold <= 1.0):
            raise ValueError(
                f"Thresholds must satisfy 0 < warning({warning_threshold}) "
                f"< critical({critical_threshold}) <= 1.0"
            )

        self._epsilon_budget = epsilon_budget
        self._delta_budget = delta_budget
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold

        # 累计追踪
        self._spend_records: List[BudgetSpent] = []
        self._epsilon_spent_naive = 0.0
        self._delta_spent_cumulative = 0.0

    @property
    def epsilon_budget(self) -> float:
        return self._epsilon_budget

    @property
    def delta_budget(self) -> float:
        return self._delta_budget

    def spend(
        self,
        epsilon: float,
        delta: float = 0.0,
        mechanism: str = 'laplace',
        query_id: Optional[str] = None,
    ) -> BudgetStatus:
        """记录一次查询的隐私预算消耗

        Args:
            epsilon: 本次查询的ε消耗
            delta: 本次查询的δ消耗 (Laplace=0, Gaussian>0)
            mechanism: 噪声机制 ('laplace' or 'gaussian')
            query_id: 可选查询标识

        Returns:
            BudgetStatus: 更新后的预算状态

        Raises:
            PrivacyBudgetExceededError: 预算已耗尽时(由调用方决定是否抛出)
        """
        if epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {epsilon}")
        if delta < 0:
            raise ValueError(f"delta must be >= 0, got {delta}")

        # 记录消耗
        record = BudgetSpent(
            epsilon_spent=epsilon,
            delta_spent=delta,
            mechanism=mechanism,
            timestamp=time.time(),
            query_id=query_id,
        )
        self._spend_records.append(record)

        # 简单求和累计
        self._epsilon_spent_naive += epsilon
        self._delta_spent_cumulative += delta

        # 计算状态
        status = self.get_status()

        # 告警日志
        if status.warning_level == BudgetWarningLevel.EXCEEDED:
            logger.error(
                f"Privacy budget EXCEEDED: ε_spent={status.epsilon_spent_cumulative:.4f} "
                f"> ε_budget={self._epsilon_budget:.4f} "
                f"(queries={status.query_count})"
            )
        elif status.warning_level == BudgetWarningLevel.CRITICAL_80:
            logger.warning(
                f"Privacy budget CRITICAL (>{self._critical_threshold:.0%}): "
                f"ε_spent={status.epsilon_spent_cumulative:.4f} / "
                f"ε_budget={self._epsilon_budget:.4f} "
                f"({status.remaining_budget_ratio:.1%} remaining, queries={status.query_count})"
            )
        elif status.warning_level == BudgetWarningLevel.WARNING_50:
            logger.warning(
                f"Privacy budget warning (>{self._warning_threshold:.0%}): "
                f"ε_spent={status.epsilon_spent_cumulative:.4f} / "
                f"ε_budget={self._epsilon_budget:.4f} "
                f"({status.remaining_budget_ratio:.1%} remaining, queries={status.query_count})"
            )

        return status

    def get_status(self) -> BudgetStatus:
        """获取当前预算状态

        使用强组合定理计算累计ε损失:
        ε_comp = √(2k·ln(1.25/δ_g))·ε_max + k·ε_max²

        其中 ε_max = max(ε_i), k = 查询次数
        """
        k = len(self._spend_records)

        if k == 0:
            return BudgetStatus(
                epsilon_total_budget=self._epsilon_budget,
                epsilon_spent_cumulative=0.0,
                epsilon_spent_naive=0.0,
                delta_total_budget=self._delta_budget,
                delta_spent_cumulative=0.0,
                query_count=0,
                warning_level=BudgetWarningLevel.OK,
                remaining_budget_ratio=1.0,
            )

        # 强组合定理: ε_comp = √(2k·ln(1/δ_g))·ε_max + k·ε_max²
        # 注: 使用ln(1/delta_g)而非ln(1.25/delta_g), 1.25系数仅用于Gaussian机制的sigma计算
        epsilon_max = max(r.epsilon_spent for r in self._spend_records)
        import math
        delta_g = self._delta_budget
        epsilon_composed = (
            math.sqrt(2 * k * math.log(1.0 / delta_g)) * epsilon_max
            + k * epsilon_max ** 2
        )

        # δ累计: δ_comp ≈ k·δ_max (保守上界)
        delta_max = max(r.delta_spent for r in self._spend_records)
        delta_composed = k * delta_max if delta_max > 0 else 0.0

        # 预算使用比率 (基于组合定理ε)
        usage_ratio = min(epsilon_composed / self._epsilon_budget, 1.0)
        remaining = max(1.0 - usage_ratio, 0.0)

        # 告警等级
        if usage_ratio >= 1.0:
            warning_level = BudgetWarningLevel.EXCEEDED
        elif usage_ratio >= self._critical_threshold:
            warning_level = BudgetWarningLevel.CRITICAL_80
        elif usage_ratio >= self._warning_threshold:
            warning_level = BudgetWarningLevel.WARNING_50
        else:
            warning_level = BudgetWarningLevel.OK

        return BudgetStatus(
            epsilon_total_budget=self._epsilon_budget,
            epsilon_spent_cumulative=epsilon_composed,
            epsilon_spent_naive=self._epsilon_spent_naive,
            delta_total_budget=self._delta_budget,
            delta_spent_cumulative=delta_composed,
            query_count=k,
            warning_level=warning_level,
            remaining_budget_ratio=remaining,
        )

    def can_spend(self, epsilon: float) -> Tuple[bool, BudgetStatus]:
        """检查是否有足够预算进行下一次查询

        使用强组合定理预测: 模拟添加本次epsilon后的组合ε损失，
        确保实际隐私损失不超过预算（与get_status()使用相同的组合定理）。

        Args:
            epsilon: 计划消耗的ε值
        Returns:
            (can_spend, status): 是否可以消耗 + 当前状态
        """
        import math
        status = self.get_status()

        # 预测: 如果花费本次epsilon，组合ε损失会是多少？
        k_projected = status.query_count + 1  # 当前查询数 + 本次查询
        epsilon_max_projected = max(
            max(r.epsilon_spent for r in self._spend_records) if self._spend_records else 0,
            epsilon,
        )
        delta_g = self._delta_budget

        # 强组合定理预测: ε_comp = √(2k·ln(1/δ_g))·ε_max + k·ε_max²
        epsilon_composed_projected = (
            math.sqrt(2 * k_projected * math.log(1.0 / delta_g)) * epsilon_max_projected
            + k_projected * epsilon_max_projected ** 2
        )

        if epsilon_composed_projected > self._epsilon_budget:
            return False, status
        return True, status

    def reset(self) -> None:
        """重置预算追踪（新会话/新用户）"""
        self._spend_records.clear()
        self._epsilon_spent_naive = 0.0
        self._delta_spent_cumulative = 0.0

    def get_spend_history(self) -> List[Dict[str, Any]]:
        """获取预算消耗历史"""
        return [
            {
                'epsilon_spent': r.epsilon_spent,
                'delta_spent': r.delta_spent,
                'mechanism': r.mechanism,
                'timestamp': r.timestamp,
                'query_id': r.query_id,
            }
            for r in self._spend_records
        ]


# ── 全局预算追踪器（按用户/会话隔离） ──

_budget_trackers: Dict[str, PrivacyBudgetTracker] = {}


def get_budget_tracker(
    user_id: str,
    epsilon_budget: float = 10.0,
    delta_budget: float = 1e-5,
) -> PrivacyBudgetTracker:
    """获取指定用户的预算追踪器（懒创建）

    Args:
        user_id: 用户标识
        epsilon_budget: ε预算上限 (仅首次创建时生效)
        delta_budget: δ预算上限 (仅首次创建时生效)
    Returns:
        PrivacyBudgetTracker
    """
    if user_id not in _budget_trackers:
        _budget_trackers[user_id] = PrivacyBudgetTracker(
            epsilon_budget=epsilon_budget,
            delta_budget=delta_budget,
        )
        logger.info(
            f"Created budget tracker for user={user_id}: "
            f"ε_budget={epsilon_budget}, δ_budget={delta_budget}"
        )
    return _budget_trackers[user_id]


def reset_budget_tracker(user_id: str) -> None:
    """重置指定用户的预算追踪器"""
    if user_id in _budget_trackers:
        _budget_trackers[user_id].reset()
        logger.info(f"Reset budget tracker for user={user_id}")


def get_all_tracker_status() -> Dict[str, Dict[str, Any]]:
    """获取所有用户的预算状态摘要"""
    result = {}
    for user_id, tracker in _budget_trackers.items():
        status = tracker.get_status()
        result[user_id] = {
            'epsilon_budget': status.epsilon_total_budget,
            'epsilon_spent': round(status.epsilon_spent_cumulative, 6),
            'epsilon_spent_naive': round(status.epsilon_spent_naive, 6),
            'delta_budget': status.delta_total_budget,
            'delta_spent': status.delta_spent_cumulative,
            'query_count': status.query_count,
            'warning_level': status.warning_level.value,
            'remaining_ratio': round(status.remaining_budget_ratio, 4),
        }
    return result
