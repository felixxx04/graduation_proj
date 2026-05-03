# Recommendation Accuracy Fix — Design Spec

**Date:** 2026-05-03
**Status:** Approved
**Scope:** Model service (`predictor.py`), training pipeline (`pipeline/runner.py`)

## Root Causes Identified

1. **Cross-candidate DDI over-penalty** — `score *= 0.05` drops correctly recommended drugs (Aspirin 0.976→0.049 due to Ibuprofen-Aspirin co-prescription warning)
2. **Disease synonym unknown words** — "pyrexia"/"febrile illness" not in encoder vocab → `__unknown__` embedding (fixed in prev session)
3. **Model blind spots for certain diseases** — e.g., SSRIs score 0.04 for depression
4. **DP noise reordering** — Laplace noise (ε=1.0, scale=0.2) can push correct drugs out of top-3

## Part B: Code Fixes (Immediate)

### B1. Downgrade cross-candidate DDI to warning-only
- File: `predictor.py` lines 624-643
- Remove `score *= 0.05` penalty
- Keep DDI warning flags for frontend display
- Drugs with matchedDisease should not be penalized by unrelated co-drug interactions

### B2. Rule-based re-ranking guard
- File: `predictor.py` `_model_rank` method
- After model scoring, boost drugs with `matchedDisease` non-null by multiplying score × 1.3
- Ensure at least 1 indication-matched drug in top-3
- Rationale: indication match is clinical ground truth, model is probabilistic

### B3. DP noise guard for matched drugs
- File: `predictor.py` `_apply_dp_noise`
- If DP noise pushes a matchedDisease drug below top-3 threshold, apply a recovery boost
- Cap noise negative impact on matched drugs at -0.15 (instead of unbounded)

## Part C: Training Data Retrain (Long-term)

### C1. Training data quality audit
- File: `pipeline/runner.py` `build_training_samples`
- Verify disease→drug indication mappings are clinically correct
- Check that each disease category has representative positive training pairs

### C2. Positive pair enrichment
- Ensure core therapeutic drugs per disease class have ≥ 5 positive training pairs
- Expand patient pool from 500 → 1000 synthetic patients
- Add more disease categories (60 → 80+)

### C3. Retrain and evaluate
- Retrain DeepFM with improved data
- Compare old vs new model on 6 test scenarios
- Replace `saved_models/best_model.pt` if quality improves

## Success Criteria

- Aspirin/Ibuprofen no longer penalized by cross-DDI
- SSRI drugs (fluoxetine, paroxetine) score ≥ 0.5 for depression
- All 6 test diseases get clinically appropriate top-3 recommendations
- DP noise does not remove matched-indication drugs from top-3
