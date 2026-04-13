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
npm run dev      # Start dev server
npm run build    # Build for production (tsc + vite build)
npm run preview  # Preview production build
```

### Backend (medical-backend/)
```bash
mvn spring-boot:run                    # Run with Maven
mvn clean package -DskipTests          # Build JAR (target/*.jar)
java -jar target/medical-backend-1.0.0.jar  # Run JAR
```

### Model Service (medical-model/)
```bash
# Create venv and install dependencies
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Database Setup (medical-backend/sql/)
```bash
mysql -u root -p < sql/schema.sql       # Create tables
mysql -u root -p < sql/init_data.sql    # Insert initial data
mysql -u root -p < sql/drug_data.sql    # Insert drug data
```

## Architecture

### Frontend Routes (src/App.tsx)
- `/login` - Public login page
- `/recommendation` - Drug recommendation (auth required)
- `/visualization` - Privacy visualization (auth required)
- `/patients`, `/privacy`, `/admin` - Admin only

### Backend Controllers
- `AuthController` - JWT authentication
- `RecommendationController` - Proxies to model service
- `PrivacyController` - Privacy config management
- `PatientController` - Patient records CRUD
- `AdminController` - User management, privacy ledger

### Model Service (Python)
- **DeepFM**: Factorization Machines + Deep neural network for drug recommendation
- **Differential Privacy**: Laplace/Gaussian noise injection on prediction scores
- **RAG Service**: ChromaDB-based retrieval for enhanced explanations

### Data Flow
1. Frontend → Backend (Spring Boot) for auth/data operations
2. Backend → Model Service for ML predictions
3. Model Service applies differential privacy before returning scores

### Database Tables
- `sys_user` - User accounts (admin/doctor/researcher roles)
- `patient` / `patient_health_record` - Patient data
- `drug` - Drug information
- `recommendation` - Recommendation history
- `privacy_ledger` - Privacy budget tracking
- `privacy_config` - User privacy settings

### Default Credentials
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| doctor1 | admin123 | doctor |
| researcher1 | admin123 | researcher |

## Key Implementation Details

### Differential Privacy
- Configurable epsilon (default 0.1) and delta (default 1e-5)
- Two noise mechanisms: Laplace (default) and Gaussian
- Privacy budget tracking in `privacy_ledger` table
- See `medical-model/app/utils/privacy.py` for noise functions

### Authentication Flow
- JWT tokens via Spring Security
- Roles: `admin`, `doctor`, `researcher`
- Frontend stores token in `authStore.tsx`
- `RequireAuthModal` and `RequireRole` components guard routes

### API Integration
- Backend runs on `localhost:8080`
- Model service on `localhost:8001`
- Backend proxies recommendation requests to model service
