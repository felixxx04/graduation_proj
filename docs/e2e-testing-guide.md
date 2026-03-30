# End-to-End Testing Guide

This guide explains how to test the complete medical recommendation system flow.

## Prerequisites

1. **MySQL 8.0+** - Running with database initialized
2. **Python 3.10+** - For model service
3. **Node.js 18+** - For frontend
4. **Java 17+** - For SpringBoot backend

## Step 1: Start All Services

### Terminal 1: MySQL Database
```bash
# Ensure MySQL is running and database is initialized
mysql -u root -p < medical-backend/sql/schema.sql
mysql -u root -p < medical-backend/sql/init_data.sql
mysql -u root -p < medical-backend/sql/drug_data.sql
```

### Terminal 2: Python Model Service
```bash
cd medical-model
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Terminal 3: SpringBoot Backend
```bash
cd medical-backend
mvn spring-boot:run
```

Backend runs at: http://localhost:8080

### Terminal 4: React Frontend
```bash
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

## Step 2: Test Login Flow

1. Open http://localhost:5173 in browser
2. Click "Login" button in header
3. Use credentials:
   - **Admin**: `admin` / `admin123`
   - **Doctor**: `doctor1` / `admin123`
   - **Researcher**: `researcher1` / `admin123`
4. Expected: Redirect to home page, username shown in header

### API Endpoint
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## Step 3: Test Patient Management

1. Login as `admin` (only admins can access patient management)
2. Navigate to "Patient Records" (患者档案) from navigation
3. **View Patients**: Should display list of patients from database
4. **Add Patient**: Click "Add Patient" button, fill form, submit
5. **Edit Patient**: Click edit icon on patient card, modify, save
6. **Delete Patient**: Click delete icon, confirm deletion
7. **Quick Recommendation**: Click "Quick Recommend" to prefill patient data

### API Endpoints
```bash
# List patients (requires auth)
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/patients

# Add patient
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","age":30,"gender":"MALE","height":170,"weight":65,"allergies":[],"chronicDiseases":[],"currentMedications":[],"medicalHistory":""}' \
  http://localhost:8080/api/patients
```

## Step 4: Test Drug Recommendation

1. Login with any account
2. Navigate to "Drug Recommendation" (用药推荐)
3. **Option A - Select Patient**: Use dropdown to select existing patient (auto-fills form)
4. **Option B - Manual Entry**: Fill patient information manually:
   - Age, Gender
   - Diagnosed diseases (comma-separated)
   - Symptoms
   - Allergies
   - Current medications
5. Toggle "Differential Privacy" switch (DP enabled/disabled)
6. Click "Start Smart Recommendation" (开始智能推荐)
7. Expected: 
   - Recommendation cards with drug names, confidence scores
   - DP comparison showing base vs DP results
   - Click drug card to see detailed info and model explainability chart
   - Privacy budget consumed (shown in sidebar)

### API Endpoint
```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"age":65,"gender":"MALE","diseases":"高血压,糖尿病","symptoms":"头晕乏力","allergies":"青霉素","currentMedications":"二甲双胍","dpEnabled":true,"topK":4}' \
  http://localhost:8080/api/recommendations/generate
```

## Step 5: Test Privacy Configuration

1. Login with any account
2. Navigate to "Privacy Config" (隐私配置)
3. **View Current Config**: See epsilon, delta, sensitivity, etc.
4. **Modify Parameters**:
   - Adjust epsilon slider (0.1 - 10)
   - Adjust delta slider
   - Adjust sensitivity
   - Select noise mechanism (Laplace/Gaussian/Geometric)
   - Select application stage (Data/Gradient/Model)
5. Click "Save Configuration" (保存配置)
6. Expected: Config saved, success message shown

### API Endpoints
```bash
# Get config
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/privacy/config

# Update config
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"epsilon":0.5,"delta":0.00001,"sensitivity":1.0,"noiseMechanism":"LAPLACE","applicationStage":"GRADIENT","privacyBudget":5.0}' \
  http://localhost:8080/api/privacy/config
```

## Step 6: Test Visualization Page

1. Login with any account
2. Navigate to "Visualization" (效果可视化)
3. View privacy budget consumption chart
4. View event history
5. Compare DP vs non-DP recommendation results

## Troubleshooting

### CORS Errors
- Check `SecurityConfig.java` allows `http://localhost:5173`
- Verify backend CORS configuration

### 401 Unauthorized
- Check JWT token in localStorage: `dp_med_auth_token_v1`
- Token may have expired (24 hour expiration)
- Try logging out and back in

### Empty Recommendations
- Verify Python model service is running on port 8001
- Check drug data is loaded in database
- Review backend logs for errors

### Privacy Budget Not Updating
- Check `privacy_ledger` table in database
- Ensure `refresh()` is called after recommendation
- Verify `privacy_config` has correct user_id mapping

## Verification Checklist

- [ ] Login works with admin/doctor1/researcher1 accounts
- [ ] Patient list displays database data
- [ ] Patient CRUD operations work
- [ ] Drug recommendation returns results
- [ ] DP toggle affects recommendation scores
- [ ] Privacy budget decrements after recommendations
- [ ] Privacy config saves successfully
- [ ] All pages accessible without errors
