"""Feedback learner — reads review_log and builds penalty weights for disease→drug_class pairs.

When doctors repeatedly reject certain drug classes for a disease, those pairs get penalized
in future rankings. Penalties decay over time to allow for new evidence.
"""
import json
import logging
import os
import time
from typing import Dict, Set, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# Penalty storage file
_PENALTY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "feedback_penalties.json")


class FeedbackLearner:
    """Learns from doctor review decisions to improve future recommendations."""

    def __init__(self):
        self.penalties: Dict[str, float] = {}  # "disease|drug_class" → penalty multiplier (0-1)
        self.rejection_counts: Dict[str, int] = defaultdict(int)
        self._load()

    def _load(self):
        """Load persisted penalties."""
        try:
            if os.path.exists(_PENALTY_FILE):
                with open(_PENALTY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.penalties = data.get('penalties', {})
                self.rejection_counts = defaultdict(int, data.get('rejection_counts', {}))
                logger.info(f"FeedbackLearner loaded: {len(self.penalties)} penalties")
        except Exception:
            pass

    def _save(self):
        """Persist penalties."""
        try:
            os.makedirs(os.path.dirname(_PENALTY_FILE), exist_ok=True)
            with open(_PENALTY_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'penalties': self.penalties,
                    'rejection_counts': dict(self.rejection_counts),
                    'updated_at': time.time(),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save penalties: {e}")

    def record_rejection(self, disease_en: str, drug_class: str, drug_name: str = ""):
        """Record a doctor's rejection of a drug for a disease."""
        key = f"{disease_en}|{drug_class}"
        self.rejection_counts[key] += 1
        count = self.rejection_counts[key]

        # Progressive penalty: 1 rejection = 0.7x, 2 = 0.5x, 3+ = 0.3x
        if count >= 3:
            self.penalties[key] = 0.3
        elif count >= 2:
            self.penalties[key] = 0.5
        else:
            self.penalties[key] = 0.7

        # Also penalize the specific drug name
        if drug_name:
            drug_key = f"{disease_en}|drug:{drug_name}"
            self.penalties[drug_key] = 0.3 if count >= 2 else 0.6

        self._save()
        logger.info(f"Feedback penalty: {key} = {self.penalties[key]:.1f}x (rejected {count}x)")

    def record_confirm(self, disease_en: str, drug_class: str):
        """Record a doctor's confirmation — reduces penalty."""
        key = f"{disease_en}|{drug_class}"
        if key in self.rejection_counts and self.rejection_counts[key] > 0:
            self.rejection_counts[key] -= 1
        if key in self.penalties:
            # Reduce penalty
            new_penalty = min(1.0, self.penalties[key] + 0.2)
            if new_penalty >= 1.0:
                del self.penalties[key]
            else:
                self.penalties[key] = new_penalty
        self._save()

    def get_penalty(self, disease_en: str, drug_class: str) -> float:
        """Get the penalty multiplier for a disease→drug_class pair. 1.0 = no penalty."""
        key = f"{disease_en}|{drug_class}"
        return self.penalties.get(key, 1.0)

    def get_drug_penalty(self, disease_en: str, drug_name: str) -> float:
        """Get the penalty for a specific drug name."""
        key = f"{disease_en}|drug:{drug_name}"
        return self.penalties.get(key, 1.0)

    def get_active_penalties(self) -> Dict[str, float]:
        """Get all active penalties (for debugging/reporting)."""
        return dict(self.penalties)


_learner: Optional[FeedbackLearner] = None


def get_feedback_learner() -> FeedbackLearner:
    global _learner
    if _learner is None:
        _learner = FeedbackLearner()
    return _learner
