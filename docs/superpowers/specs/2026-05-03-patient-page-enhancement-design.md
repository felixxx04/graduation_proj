# Patient Page Enhancement — Design Spec

**Date:** 2026-05-03
**Status:** Approved
**Scope:** Frontend (`PatientRecords.tsx`, `patientStore.tsx`), Backend (`PatientController`, `PatientService`, `PatientRequest`, `RecommendationController`)

## Part 1: Recommendation History Tab

### Motivation
Recommendations are saved to MySQL `recommendation` table but there is no way to view them in the UI.

### Design
- Add a "推荐记录" tab to the patient detail panel in `PatientRecords.tsx`
- When selected, fetch the patient's recommendation history from a new backend endpoint
- Display as a simple table: drug name, disease, date, DP status

### Backend
- New endpoint: `GET /api/recommendations?patientId={id}`
- `RecommendationController.getByPatientId()` delegates to `RecommendationService.getHistoryByPatientId()`
- `RecommendationRepository.findByPatientId()` already exists — just needs wiring

### Frontend
- `patientStore.tsx`: add `fetchRecommendationHistory(patientId)` method
- `PatientRecords.tsx`: add Tab component with 3 tabs (基本信息 / 推荐记录 / 临床指标)
- Table columns: recommended drugs, matched disease, date, DP status

## Part 2: Clinical Metrics Tab

### Motivation
The v2 clinical fields (renal function, liver function, smoking, drinking, blood pressure, blood sugar, HbA1c, cholesterol, heart rate) exist in DB and entity layer but have NO UI for data entry. The recommendation page shows a warning about missing data with nowhere to fill it in.

### Design
- Add "临床指标" tab to patient detail panel
- Form fields with dropdowns for categorical values, number inputs for numeric values
- Save button writes to `patient_health_record` table via backend API

### Field Specifications

| Field | Type | Options / Range |
|-------|------|-----------------|
| renalFunction | dropdown | 正常 / 轻度受损 / 中度受损 / 重度受损 / 未知 |
| hepaticFunction | dropdown | 正常 / 轻度受损 / 中度受损 / 重度受损 / 未知 |
| smokingStatus | dropdown | 从不吸烟 / 已戒烟 / 吸烟 / 未知 |
| drinkingStatus | dropdown | 不饮酒 / 偶尔饮酒 / 经常饮酒 / 大量饮酒 / 未知 |
| bloodPressureSystolic | number | 80-250 mmHg |
| bloodPressureDiastolic | number | 40-150 mmHg |
| fastingGlucose | number | 2.0-30.0 mmol/L |
| hba1c | number | 3.0-20.0 % |
| cholesterolTotal | number | 2.0-15.0 mmol/L |
| cholesterolLdl | number | 1.0-10.0 mmol/L |
| heartRate | number | 30-250 bpm |

### Backend Changes
- `PatientRequest.java`: add all v2 clinical fields
- `PatientService.updateHealthRecord()`: write clinical fields
- New endpoint: `PUT /api/patients/{id}/clinical` to update clinical metrics

### Frontend Changes  
- `patientStore.tsx`: add `ClinicalMetrics` type, `updateClinicalMetrics()` method
- `PatientRecords.tsx`: add clinical form in new tab, save handler

## Data Flow

```
Clinical Form (React) → patientStore.updateClinicalMetrics()
  → PUT /api/patients/{id}/clinical
    → PatientService.updateHealthRecord()
      → patient_health_record table UPDATE

Recommendation History (React) → patientStore.fetchRecommendationHistory()
  → GET /api/recommendations?patientId={id}
    → RecommendationService.getHistoryByPatientId()
      → recommendation table SELECT
```

## Testing

- [ ] Verify clinical metrics save and re-load on patient detail
- [ ] Verify recommendation history shows correct records for patient
- [ ] Verify "数据缺失" warning disappears after filling clinical fields
- [ ] Verify empty states (no history, all fields unknown) render gracefully
