# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

差分隐私保护的AI驱动的个性化医疗用药推荐系统 (Differential Privacy-Protected AI-Powered Personalized Medical Drug Recommendation System)

Three-tier architecture:
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS (port 5173)
- **Backend**: Spring Boot 3.2 + MyBatis + MySQL (port 8080)
- **Model Service**: Python FastAPI + PyTorch DeepFM (port 8001)

## Commands

### Frontend (root directory)
```bash
npm run dev              # Start dev server (port 5173)
npm run build            # Build for production (tsc + vite build)
npm run preview          # Preview production build
npx vitest run           # Run tests
npx vitest run src/lib/__tests__/privacy.test.ts  # Run single test file
npx vitest --coverage    # Run tests with coverage
```

### Backend (medical-backend/)
```bash
mvn spring-boot:run                    # Run with Maven
mvn clean package -DskipTests          # Build JAR (target/*.jar)
java -jar target/medical-backend-1.0.0.jar  # Run JAR
mvn test                               # Run backend tests
```

### Model Service (medical-model/)
```bash
# Setup (first time)
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Run experiments
python scripts/run_phase2_experiments.py   # Phase 2 training experiments
python scripts/run_phase1_experiments.py   # Phase 1 experiments (not yet completed)
python scripts/run_comparison_experiments.py  # Comparison experiments (not yet run)
```

### Database Setup (medical-backend/sql/)
```bash
mysql -u root -p < sql/schema.sql       # Create tables
mysql -u root -p < sql/init_data.sql    # Insert initial data
mysql -u root -p < sql/drug_data.sql    # Insert drug data
```

## Architecture

### Three-Layer Recommendation Architecture (CRITICAL)

This is the core architectural pattern. Understanding it is essential for working on the recommendation system:

1. **Layer 1: SafetyFilter** — Deterministic hard exclusion. Absolute contraindications, allergy conflicts, major drug interactions, pregnancy category X, pediatric contraindications. **DP noise NEVER affects this layer.**

2. **Layer 2: RuleMarker** — Soft flagging (not exclusion). Relative contraindications, moderate interactions, pregnancy C/D warnings. Adds `requires_review` and `safetyType` flags but does not change the candidate set.

3. **Layer 3: DeepFM Ranking** — Personalized scoring of safe candidates only. **DP noise is applied ONLY at this layer.** If model is loaded, uses real DeepFM inference; otherwise falls back to rule-based "demo mode" (clearly labeled).

### Data Flow

1. Frontend → Backend (Spring Boot) for auth/data operations
2. Backend → Model Service (`/model/predict`) for ML predictions
3. On startup, backend loads all drugs from MySQL → model service (`/model/load-drugs`)
4. Model service applies 3-layer architecture + DP noise before returning scores

### Frontend Routes (src/App.tsx)
- `/login` - Public login page
- `/recommendation` - Drug recommendation (requires auth, modal popup if not logged in)
- `/visualization` - Privacy visualization (requires auth)
- `/patients`, `/privacy`, `/admin` - Requires admin role

### Frontend State Management

All state is React Context-based (no Redux/Zustand). Three providers wrap `<App />`:
- `AuthProvider` (authStore.tsx) — JWT in localStorage, login/logout, `/api/auth/me` bootstrap
- `PatientStoreProvider` (patientStore.tsx) — Patient CRUD via `/api/patients`
- `PrivacyStoreProvider` (privacyStore.tsx) — Config/budget/events via `/api/privacy/*`

Roles simplified in frontend: backend (admin/doctor/researcher) → frontend (admin/user). Guard components: `RequireAuthModal` (redirects with login modal), `RequireRole` (redirects to `/forbidden`).

### Dual Recommendation Engine

Frontend has a LOCAL demo engine (`src/lib/recommendation.ts`) with 6 hardcoded Chinese drugs for demo/offline mode. Production uses backend API. The `DrugRecommendation.tsx` page calls `/api/recommendations/generate` for real results.

### Backend Controllers
- `AuthController` — JWT authentication (`/api/auth/login`, `/api/auth/me`)
- `RecommendationController` — Proxies to model service, saves to DB, budget check
- `PrivacyController` — Privacy config/budget/events management
- `PatientController` — Patient records CRUD (ADMIN+DOCTOR only)
- `AdminController` — User management, training proxy (ADMIN only)
- `HealthController` — `/api/health`

### Model Service Endpoints
- `POST /model/predict` — Drug recommendation (main endpoint)
- `POST /model/train` — Model training
- `POST /model/load-drugs` — Load drug data from backend
- `GET /model/status` — Model status
- `GET /model/privacy/budget` — Budget status
- `POST /model/privacy/budget/reset` — Reset budget
- `GET /model/audit/logs` — Query audit logs
- `POST /model/audit/consent` — Log informed consent

### Database Tables
- `sys_user` — User accounts (admin/doctor/researcher roles, BCrypt passwords)
- `patient` / `patient_health_record` — Patient data (chronic_diseases/alleries/medications as JSON)
- `drug` — Drug catalog (indications/contraindications/side_effects/interactions as JSON)
- `recommendation` — Recommendation history (input_data/result_data as JSON)
- `privacy_ledger` — Privacy budget tracking events
- `privacy_config` — Per-user DP config (epsilon, delta, noise_mechanism, budget)
- `system_config` / `operation_log` — System settings and audit

## Key Implementation Details

### Differential Privacy

**Dual implementation** — both frontend and model service implement DP noise independently:
- Frontend `src/lib/privacy.ts`: Laplace/Gaussian/Geometric for demo mode
- Model service `app/utils/privacy.py`: numpy-based Laplace/Gaussian for production
- Same formulas: Laplace scale = sensitivity/epsilon, Gaussian sigma = sensitivity * sqrt(2*ln(1.25/delta))/epsilon

**Budget dual tracking** — NOT synchronized between backend and model service:
- Backend: MySQL `privacy_config.budget_used` + `privacy_ledger` (persistent, per-user)
- Model service: In-memory `PrivacyBudgetTracker` with strong composition theorem (ephemeral)

**DP noise application** (in predictor.py `_apply_dp_noise()`):
- Clinical safety threshold: scores < 0.15 are zeroed (public threshold, DP post-processing theorem)
- Ceiling: `min(1.0, raw_score + 0.35)` prevents noise amplifying low scores beyond 3.5x
- Confidence intervals calculated (95% CI)
- `dpAnomaly` flag: marks when noise significantly changes ranking direction

### Translation Pipeline (English → Chinese)

Model service response fields are translated from English to Chinese before returning to frontend:
- `drug_translator.py` — Drug name EN→CN translation
- `translation_mapper.py` — Unified mapper for conditions, drug classes, side effects, enum values
- `disease_mapper.py` — Chinese symptom/disease to English disease mapping
- Response includes both `drugName` (Chinese) and `englishName` (original English)

### Authentication Flow
- JWT tokens via Spring Security (HMAC-SHA, 24-hour expiration, min 32-char secret)
- Frontend stores token in localStorage via `authStore.tsx`
- `api.ts` auto-attaches `Authorization: Bearer <token>` to every request
- Role-based endpoint authorization in Spring Security config

### DeepFM Model Architecture
- MultiFieldFM: Merged embedding (single nn.Embedding with field_offsets) — Opacus-compatible
- Deep: MLP with LayerNorm + ReLU + per-layer differentiated dropout
- DeepFM: FM + Deep + continuous feature bypass (age_raw, bmi_raw, gfr_raw, liver_score_raw)
- Returns raw logits; sigmoid applied manually at inference
- 16 categorical fields + 4 continuous features (718 drug candidates)
- embed_dim=16, hidden_dims=[64, 32]

### Feature Schema (pipeline/schema.py)
16 categorical fields: age_group, gender, bmi_group, renal_function, hepatic_function, primary_disease, secondary_disease, allergy_severity, drug_class, med_class_1-4, pregnancy_cat, rx_otc, drug_candidate
4 continuous features: age_raw, bmi_raw, gfr_raw, liver_score_raw

## Port Configuration

**IMPORTANT**: `application.yml` sets model-service URL to `http://localhost:8002`, but `ModelServiceConfig.java` defaults to `http://localhost:8001` and the FastAPI service runs on port 8001. If the YAML property is active, requests will fail. Verify which port is actually used in your deployment.

## Default Credentials
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| doctor1 | admin123 | doctor |
| researcher1 | admin123 | researcher |

## Current Training Status

Phase 2 experiments completed (2026-04-26). Results in `experiments/results/phase2/`:
- `no_dp_baseline_v5`: AUC-PR=0.8995, zero safety violations
- `dp_finetune_eps1_v5`: AUC-PR=0.8998 (DP finetune, eps=1.0)
- `dp_finetune_eps05_v5`: AUC-PR=0.9011 (DP finetune, eps=0.5) — **best model**

**NOTE**: `saved_models/` currently contains the older baseline (embed_dim=8, AUC-PR=0.749). The Phase 2 best model (embed_dim=16, AUC-PR=0.901) is in `experiments/results/phase2/dp_finetune_eps05_v5/`. Deploy the Phase 2 model to `saved_models/` for the production service to use it.