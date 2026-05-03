# Patient Page Enhancement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add recommendation history tab and clinical metrics form tab to patient detail panel, plus backend APIs to support both.

**Architecture:** Backend-first approach — new REST endpoints for recommendation history query and clinical metrics update, then frontend tabs consume them. Follows existing patterns: `PatientRequest` DTO style, `ApiResponse` envelope, `patientStore` context pattern.

**Tech Stack:** Spring Boot 3.2 + MyBatis (Java) / React 18 + TypeScript + Tailwind CSS (frontend)

---

## Task 1: Backend — Recommendation history endpoint

**Files:**
- Modify: `medical-backend/src/main/java/com/medical/controller/RecommendationController.java`
- Modify: `medical-backend/src/main/java/com/medical/service/RecommendationService.java`
- Modify: `medical-backend/src/main/java/com/medical/dto/response/RecommendationHistoryItem.java` (create)
- Modify: `medical-backend/src/main/java/com/medical/entity/Recommendation.java`

- [ ] **Step 1: Create RecommendationHistoryItem DTO**

Create: `medical-backend/src/main/java/com/medical/dto/response/RecommendationHistoryItem.java`

```java
package com.medical.dto.response;

import lombok.Builder;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class RecommendationHistoryItem {
    private Long id;
    private Long patientId;
    private String patientName;
    private List<String> recommendedDrugs;
    private String primaryDisease;
    private Boolean dpEnabled;
    private Double epsilonUsed;
    private LocalDateTime createdAt;
}
```

- [ ] **Step 2: Read Recommendation entity**

Read `medical-backend/src/main/java/com/medical/entity/Recommendation.java` to understand existing fields.

Expected fields: `id`, `patientId`, `userId`, `inputData` (JSON String), `resultData` (JSON String), `dpEnabled`, `epsilonUsed`, `recommendationType`, `createdAt`.

- [ ] **Step 3: Add service method**

In `medical-backend/src/main/java/com/medical/service/RecommendationService.java`, add method after `saveRecommendation()`:

```java
public List<RecommendationHistoryItem> getHistoryByPatientId(Long patientId) {
    List<Recommendation> records = recommendationRepository.findByPatientId(patientId);
    return records.stream().map(rec -> {
        List<String> drugNames = new ArrayList<>();
        String primaryDisease = "";
        try {
            Map<String, Object> result = objectMapper.readValue(rec.getResultData(), Map.class);
            Object selected = result.get("selected");
            if (selected instanceof List) {
                for (Object item : (List<?>) selected) {
                    if (item instanceof Map) {
                        Map<?, ?> m = (Map<?, ?>) item;
                        Object name = m.get("drugName");
                        if (name != null) drugNames.add(String.valueOf(name));
                    }
                }
            }
            Object inputData = rec.getInputData();
            if (inputData != null) {
                Map<String, Object> input = objectMapper.readValue(
                    inputData instanceof String ? (String) inputData : String.valueOf(inputData),
                    Map.class
                );
                Object diseases = input.get("diseases");
                if (diseases instanceof String) primaryDisease = (String) diseases;
            }
        } catch (Exception ignored) { }

        return RecommendationHistoryItem.builder()
            .id(rec.getId())
            .patientId(rec.getPatientId())
            .recommendedDrugs(drugNames)
            .primaryDisease(primaryDisease)
            .dpEnabled(rec.getDpEnabled())
            .epsilonUsed(rec.getEpsilonUsed())
            .createdAt(rec.getCreatedAt())
            .build();
    }).collect(Collectors.toList());
}
```

Required imports at top of file:
```java
import com.medical.dto.response.RecommendationHistoryItem;
import java.util.ArrayList;
import java.util.stream.Collectors;
```

- [ ] **Step 4: Add controller endpoint**

In `medical-backend/src/main/java/com/medical/controller/RecommendationController.java`, add:

```java
@GetMapping
public ApiResponse<List<RecommendationHistoryItem>> getHistory(
        @RequestParam(required = false) Long patientId) {
    if (patientId != null) {
        return ApiResponse.success(recommendationService.getHistoryByPatientId(patientId));
    }
    return ApiResponse.success(recommendationService.getAllHistory());
}
```

Required imports:
```java
import com.medical.dto.response.RecommendationHistoryItem;
import java.util.List;
```

- [ ] **Step 5: Add getAllHistory to service**

In `RecommendationService.java`, add:

```java
public List<RecommendationHistoryItem> getAllHistory() {
    List<Recommendation> records = recommendationRepository.findAll();
    return records.stream().map(rec -> {
        List<String> drugNames = new ArrayList<>();
        try {
            Map<String, Object> result = objectMapper.readValue(rec.getResultData(), Map.class);
            Object selected = result.get("selected");
            if (selected instanceof List) {
                for (Object item : (List<?>) selected) {
                    if (item instanceof Map) {
                        Map<?, ?> m = (Map<?, ?>) item;
                        Object name = m.get("drugName");
                        if (name != null) drugNames.add(String.valueOf(name));
                    }
                }
            }
        } catch (Exception ignored) { }

        return RecommendationHistoryItem.builder()
            .id(rec.getId())
            .patientId(rec.getPatientId())
            .recommendedDrugs(drugNames)
            .dpEnabled(rec.getDpEnabled())
            .epsilonUsed(rec.getEpsilonUsed())
            .createdAt(rec.getCreatedAt())
            .build();
    }).collect(Collectors.toList());
}
```

- [ ] **Step 6: Verify compilation**

Run: `cd medical-backend && mvn compile -q`
Expected: BUILD SUCCESS

---

## Task 2: Backend — Clinical metrics update endpoint

**Files:**
- Create: `medical-backend/src/main/java/com/medical/dto/request/ClinicalMetricsRequest.java`
- Modify: `medical-backend/src/main/java/com/medical/dto/request/PatientRequest.java`
- Modify: `medical-backend/src/main/java/com/medical/controller/PatientController.java`
- Modify: `medical-backend/src/main/java/com/medical/service/PatientService.java`

- [ ] **Step 1: Create ClinicalMetricsRequest DTO**

Create: `medical-backend/src/main/java/com/medical/dto/request/ClinicalMetricsRequest.java`

```java
package com.medical.dto.request;

import lombok.Data;
import java.math.BigDecimal;

@Data
public class ClinicalMetricsRequest {
    private String renalFunction;
    private String hepaticFunction;
    private String smokingStatus;
    private String drinkingStatus;
    private Integer bloodPressureSystolic;
    private Integer bloodPressureDiastolic;
    private BigDecimal fastingGlucose;
    private BigDecimal hba1c;
    private BigDecimal cholesterolTotal;
    private BigDecimal cholesterolLdl;
    private Integer heartRate;
}
```

- [ ] **Step 2: Add v2 fields to PatientRequest**

In `PatientRequest.java`, add before the closing brace:

```java
// v2: 临床指标
private String renalFunction;
private String hepaticFunction;
private String smokingStatus;
private String drinkingStatus;
private Integer bloodPressureSystolic;
private Integer bloodPressureDiastolic;
private BigDecimal fastingGlucose;
private BigDecimal hba1c;
private BigDecimal cholesterolTotal;
private BigDecimal cholesterolLdl;
private Integer heartRate;
```

Required import: `import java.math.BigDecimal;`

- [ ] **Step 3: Update createHealthRecord to write v2 fields**

In `PatientService.java`, in `createHealthRecord()` method after `record.setIsLatest(true)`:

```java
record.setRenalFunction(request.getRenalFunction());
record.setHepaticFunction(request.getHepaticFunction());
record.setSmokingStatus(request.getSmokingStatus());
record.setDrinkingStatus(request.getDrinkingStatus());
record.setBloodPressureSystolic(request.getBloodPressureSystolic());
record.setBloodPressureDiastolic(request.getBloodPressureDiastolic());
record.setFastingGlucose(request.getFastingGlucose());
record.setHba1c(request.getHba1c());
record.setCholesterolTotal(request.getCholesterolTotal());
record.setCholesterolLdl(request.getCholesterolLdl());
record.setHeartRate(request.getHeartRate());
```

- [ ] **Step 4: Add clinical update endpoint to PatientController**

In `PatientController.java`, add:

```java
@PutMapping("/{id}/clinical")
public ApiResponse<Void> updateClinicalMetrics(
        @PathVariable Long id,
        @RequestBody ClinicalMetricsRequest request) {
    patientService.updateClinicalMetrics(id, request);
    return ApiResponse.success("临床指标更新成功", null);
}
```

Required import: `import com.medical.dto.request.ClinicalMetricsRequest;`

- [ ] **Step 5: Add updateClinicalMetrics to PatientService**

In `PatientService.java`, add method:

```java
public void updateClinicalMetrics(Long patientId, ClinicalMetricsRequest request) {
    HealthRecord latest = healthRecordRepository.findLatestByPatientId(patientId);
    if (latest == null) {
        // Create a minimal record with clinical data only
        latest = new HealthRecord();
        latest.setPatientId(patientId);
        latest.setRecordDate(LocalDate.now());
        latest.setIsLatest(true);
    }
    if (request.getRenalFunction() != null)
        latest.setRenalFunction(request.getRenalFunction());
    if (request.getHepaticFunction() != null)
        latest.setHepaticFunction(request.getHepaticFunction());
    if (request.getSmokingStatus() != null)
        latest.setSmokingStatus(request.getSmokingStatus());
    if (request.getDrinkingStatus() != null)
        latest.setDrinkingStatus(request.getDrinkingStatus());
    if (request.getBloodPressureSystolic() != null)
        latest.setBloodPressureSystolic(request.getBloodPressureSystolic());
    if (request.getBloodPressureDiastolic() != null)
        latest.setBloodPressureDiastolic(request.getBloodPressureDiastolic());
    if (request.getFastingGlucose() != null)
        latest.setFastingGlucose(request.getFastingGlucose());
    if (request.getHba1c() != null)
        latest.setHba1c(request.getHba1c());
    if (request.getCholesterolTotal() != null)
        latest.setCholesterolTotal(request.getCholesterolTotal());
    if (request.getCholesterolLdl() != null)
        latest.setCholesterolLdl(request.getCholesterolLdl());
    if (request.getHeartRate() != null)
        latest.setHeartRate(request.getHeartRate());

    if (latest.getId() == null) {
        healthRecordRepository.insert(latest);
    } else {
        healthRecordRepository.update(latest);
    }
}
```

Required imports:
```java
import com.medical.dto.request.ClinicalMetricsRequest;
import java.time.LocalDate;
```

- [ ] **Step 6: Verify compilation**

Run: `cd medical-backend && mvn compile -q`
Expected: BUILD SUCCESS

---

## Task 3: Frontend — patientStore types and methods

**Files:**
- Modify: `src/lib/patientStore.tsx`

- [ ] **Step 1: Add types to patientStore.tsx**

After the existing `Patient` interface (line 20), add:

```typescript
export interface RecommendationRecord {
  id: number
  patientId: number
  recommendedDrugs: string[]
  primaryDisease: string
  dpEnabled: boolean
  epsilonUsed: number | null
  createdAt: string
}

export interface ClinicalMetrics {
  renalFunction: string
  hepaticFunction: string
  smokingStatus: string
  drinkingStatus: string
  bloodPressureSystolic: number | null
  bloodPressureDiastolic: number | null
  fastingGlucose: number | null
  hba1c: number | null
  cholesterolTotal: number | null
  cholesterolLdl: number | null
  heartRate: number | null
}
```

- [ ] **Step 2: Add methods to PatientStoreState type**

In the `PatientStoreState` type, add after `deletePatient`:

```typescript
fetchRecommendationHistory: (patientId: string) => Promise<RecommendationRecord[]>
updateClinicalMetrics: (patientId: string, metrics: ClinicalMetrics) => Promise<void>
```

- [ ] **Step 3: Implement fetchRecommendationHistory**

In the `PatientStoreProvider` component, add after `deletePatient`:

```typescript
const fetchRecommendationHistory = useCallback<PatientStoreState['fetchRecommendationHistory']>(
  async (patientId) => {
    const data = await api.get<RecommendationRecord[]>(`/api/recommendations?patientId=${patientId}`)
    return data
  }, []
)
```

- [ ] **Step 4: Implement updateClinicalMetrics**

In the `PatientStoreProvider`, add after `fetchRecommendationHistory`:

```typescript
const updateClinicalMetrics = useCallback<PatientStoreState['updateClinicalMetrics']>(
  async (patientId, metrics) => {
    await api.put<void>(`/api/patients/${patientId}/clinical`, metrics)
  }, []
)
```

- [ ] **Step 5: Add to useMemo value**

In the `useMemo`, add the new methods:

```typescript
fetchRecommendationHistory,
updateClinicalMetrics,
```

---

## Task 4: Frontend — PatientRecords tabs

**Files:**
- Modify: `src/pages/PatientRecords.tsx`

- [ ] **Step 1: Add imports**

Add to existing imports:

```typescript
import { usePatientStore, type ClinicalMetrics, type RecommendationRecord } from '@/lib/patientStore'
```

- [ ] **Step 2: Add state variables**

Add inside the `PatientRecords` component, after existing `useState` declarations:

```typescript
const [activeTab, setActiveTab] = useState<Record<string, 'basic' | 'history' | 'clinical'>>({})
const [historyCache, setHistoryCache] = useState<Record<string, RecommendationRecord[]>>({})
const [historyLoading, setHistoryLoading] = useState(false)
const [clinicalForm, setClinicalForm] = useState<ClinicalMetrics>({
  renalFunction: '', hepaticFunction: '', smokingStatus: '', drinkingStatus: '',
  bloodPressureSystolic: null, bloodPressureDiastolic: null,
  fastingGlucose: null, hba1c: null,
  cholesterolTotal: null, cholesterolLdl: null, heartRate: null,
})
const [clinicalSaving, setClinicalSaving] = useState(false)
const { fetchRecommendationHistory, updateClinicalMetrics } = usePatientStore()
```

- [ ] **Step 3: Add tab loading handler**

```typescript
const handleTabChange = useCallback(async (patientId: string, tab: 'basic' | 'history' | 'clinical') => {
  setActiveTab(prev => ({ ...prev, [patientId]: tab }))
  if (tab === 'history' && !historyCache[patientId]) {
    setHistoryLoading(true)
    try {
      const records = await fetchRecommendationHistory(patientId)
      setHistoryCache(prev => ({ ...prev, [patientId]: records }))
    } catch { /* silently fail */ }
    setHistoryLoading(false)
  }
}, [fetchRecommendationHistory, historyCache])
```

- [ ] **Step 4: Add clinical save handler**

```typescript
const handleClinicalSave = useCallback(async (patientId: string) => {
  setClinicalSaving(true)
  try {
    await updateClinicalMetrics(patientId, clinicalForm)
  } finally {
    setClinicalSaving(false)
  }
}, [clinicalForm, updateClinicalMetrics])
```

- [ ] **Step 5: Replace expanded content with tabs**

In the expanded panel section (starting around line 416), replace the content between `<div className="animate-fade-in...">` and its closing `</div>` with the tab UI.

The full replacement for the expanded panel content block (lines 416-467):

```tsx
<AnimatePresence>
  {isExpanded && (
    <div className="animate-fade-in overflow-hidden border-t border-white/[0.06]">
      {/* Tab bar */}
      <div className="flex border-b border-white/[0.06]">
        {(['basic', 'history', 'clinical'] as const).map((tab) => (
          <button
            key={tab}
            className={`px-4 py-2.5 text-xs font-medium transition-colors cursor-pointer ${
              (activeTab[patient.id] || 'basic') === tab
                ? 'text-brand-sky border-b-2 border-brand-sky'
                : 'text-muted-foreground hover:text-foreground border-b-2 border-transparent'
            }`}
            onClick={() => handleTabChange(patient.id, tab)}
          >
            {tab === 'basic' ? '基本信息' : tab === 'history' ? '推荐记录' : '临床指标'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="px-4 pb-4">
        {(activeTab[patient.id] || 'basic') === 'basic' && (
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div>
              <h4 className="mb-2 text-sm font-semibold text-brand-sky">当前用药</h4>
              <div className="space-y-1.5">
                {patient.currentMedications.length > 0 ? patient.currentMedications.map((medication) => (
                  <div key={medication} className="flex items-center gap-2 rounded-sm bg-brand-sky/4 border border-brand-sky/10 p-2">
                    <div className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-gradient-to-br from-brand-sky to-sky-600" />
                    <span className="text-sm">{medication}</span>
                  </div>
                )) : <p className="text-xs text-muted-foreground">无</p>}
              </div>
            </div>
            <div>
              <h4 className="mb-2 text-sm font-semibold text-brand-teal">过敏史</h4>
              <div className="space-y-1.5">
                {patient.allergies.length > 0 ? patient.allergies.map((allergy) => (
                  <div key={allergy} className="flex items-center gap-2 rounded-sm border border-destructive/20 bg-destructive/4 p-2">
                    <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-destructive" />
                    <span className="text-sm text-destructive">{allergy}</span>
                  </div>
                )) : <p className="text-xs text-muted-foreground">无过敏史</p>}
              </div>
            </div>
            <div>
              <h4 className="mb-2 text-sm font-semibold">体格信息</h4>
              <div className="space-y-1.5 text-sm">
                <div className="flex justify-between rounded-sm bg-surface p-2">
                  <span className="text-muted-foreground">身高</span>
                  <span className="font-semibold">{patient.height} cm</span>
                </div>
                <div className="flex justify-between rounded-sm bg-surface p-2">
                  <span className="text-muted-foreground">体重</span>
                  <span className="font-semibold">{patient.weight} kg</span>
                </div>
                <div className="flex justify-between rounded-sm bg-surface p-2">
                  <span className="text-muted-foreground">BMI</span>
                  <span className={`font-semibold ${bmiColor}`}>{bmi.toFixed(1)} ({bmiText})</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {(activeTab[patient.id] || 'basic') === 'history' && (
          <div className="mt-4">
            {historyLoading ? (
              <p className="text-sm text-muted-foreground">加载中...</p>
            ) : (historyCache[patient.id] || []).length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无推荐记录</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.06] text-muted-foreground">
                      <th className="py-2 text-left font-medium">推荐药物</th>
                      <th className="py-2 text-left font-medium">疾病</th>
                      <th className="py-2 text-left font-medium">时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(historyCache[patient.id] || []).map((rec) => (
                      <tr key={rec.id} className="border-b border-white/[0.03]">
                        <td className="py-2 pr-2">{rec.recommendedDrugs.slice(0, 3).join('、')}</td>
                        <td className="py-2 pr-2">{rec.primaryDisease || '-'}</td>
                        <td className="py-2 text-muted-foreground">{rec.createdAt ? rec.createdAt.replace('T', ' ').substring(0, 16) : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {(activeTab[patient.id] || 'basic') === 'clinical' && (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {/* Organ function */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">肾功能</Label>
                <select value={clinicalForm.renalFunction} onChange={(e) => setClinicalForm({...clinicalForm, renalFunction: e.target.value})}
                  className="flex h-9 w-full rounded-sm border border-white/[0.06] bg-surface-elevated px-3 py-1 text-xs focus-visible:outline-none focus-visible:border-brand-sky">
                  <option value="">未知</option>
                  <option value="normal">正常</option>
                  <option value="mild_impairment">轻度受损</option>
                  <option value="moderate_impairment">中度受损</option>
                  <option value="severe_impairment">重度受损</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">肝功能</Label>
                <select value={clinicalForm.hepaticFunction} onChange={(e) => setClinicalForm({...clinicalForm, hepaticFunction: e.target.value})}
                  className="flex h-9 w-full rounded-sm border border-white/[0.06] bg-surface-elevated px-3 py-1 text-xs focus-visible:outline-none focus-visible:border-brand-sky">
                  <option value="">未知</option>
                  <option value="normal">正常</option>
                  <option value="mild_impairment">轻度受损</option>
                  <option value="moderate_impairment">中度受损</option>
                  <option value="severe_impairment">重度受损</option>
                </select>
              </div>
              {/* Lifestyle */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">吸烟状态</Label>
                <select value={clinicalForm.smokingStatus} onChange={(e) => setClinicalForm({...clinicalForm, smokingStatus: e.target.value})}
                  className="flex h-9 w-full rounded-sm border border-white/[0.06] bg-surface-elevated px-3 py-1 text-xs focus-visible:outline-none focus-visible:border-brand-sky">
                  <option value="">未知</option>
                  <option value="never">从不吸烟</option>
                  <option value="former">已戒烟</option>
                  <option value="current">吸烟</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">饮酒状态</Label>
                <select value={clinicalForm.drinkingStatus} onChange={(e) => setClinicalForm({...clinicalForm, drinkingStatus: e.target.value})}
                  className="flex h-9 w-full rounded-sm border border-white/[0.06] bg-surface-elevated px-3 py-1 text-xs focus-visible:outline-none focus-visible:border-brand-sky">
                  <option value="">未知</option>
                  <option value="none">不饮酒</option>
                  <option value="occasional">偶尔饮酒</option>
                  <option value="regular">经常饮酒</option>
                  <option value="heavy">大量饮酒</option>
                </select>
              </div>
              {/* Vital signs */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">收缩压 (mmHg)</Label>
                <Input type="number" value={clinicalForm.bloodPressureSystolic ?? ''}
                  onChange={(e) => setClinicalForm({...clinicalForm, bloodPressureSystolic: e.target.value ? Number(e.target.value) : null})}
                  className="h-9 text-xs" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">舒张压 (mmHg)</Label>
                <Input type="number" value={clinicalForm.bloodPressureDiastolic ?? ''}
                  onChange={(e) => setClinicalForm({...clinicalForm, bloodPressureDiastolic: e.target.value ? Number(e.target.value) : null})}
                  className="h-9 text-xs" />
              </div>
              {/* Labs */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">空腹血糖 (mmol/L)</Label>
                <Input type="number" step="0.1" value={clinicalForm.fastingGlucose ?? ''}
                  onChange={(e) => setClinicalForm({...clinicalForm, fastingGlucose: e.target.value ? Number(e.target.value) : null})}
                  className="h-9 text-xs" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">糖化血红蛋白 (%)</Label>
                <Input type="number" step="0.1" value={clinicalForm.hba1c ?? ''}
                  onChange={(e) => setClinicalForm({...clinicalForm, hba1c: e.target.value ? Number(e.target.value) : null})}
                  className="h-9 text-xs" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">总胆固醇 (mmol/L)</Label>
                <Input type="number" step="0.1" value={clinicalForm.cholesterolTotal ?? ''}
                  onChange={(e) => setClinicalForm({...clinicalForm, cholesterolTotal: e.target.value ? Number(e.target.value) : null})}
                  className="h-9 text-xs" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">LDL胆固醇 (mmol/L)</Label>
                <Input type="number" step="0.1" value={clinicalForm.cholesterolLdl ?? ''}
                  onChange={(e) => setClinicalForm({...clinicalForm, cholesterolLdl: e.target.value ? Number(e.target.value) : null})}
                  className="h-9 text-xs" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">心率 (bpm)</Label>
                <Input type="number" value={clinicalForm.heartRate ?? ''}
                  onChange={(e) => setClinicalForm({...clinicalForm, heartRate: e.target.value ? Number(e.target.value) : null})}
                  className="h-9 text-xs" />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <Button size="sm" className="gap-1.5 cursor-pointer" disabled={clinicalSaving}
                onClick={() => handleClinicalSave(patient.id)}>
                <Save className="h-3.5 w-3.5" />
                {clinicalSaving ? '保存中...' : '保存临床指标'}
              </Button>
            </div>
          </div>
        )}

        {(activeTab[patient.id] || 'basic') === 'basic' && patient.medicalHistory && (
          <div className="mt-4 border-t border-white/[0.06] pt-4">
            <h4 className="mb-1.5 text-sm font-semibold">既往病史</h4>
            <TextExpander text={patient.medicalHistory} maxLines={3} />
          </div>
        )}
      </div>
    </div>
  )}
</AnimatePresence>
```

- [ ] **Step 6: Add Label import if not already present**

Check existing imports in `PatientRecords.tsx` for `Label` from `@/components/ui/label`. If not present, add:

```typescript
import { Label } from '@/components/ui/label'
```

- [ ] **Step 7: Type-check frontend**

Run: `cd D:/grad_medical && npx tsc --noEmit --pretty`
Expected: No errors

---

## Task 5: Verification

- [ ] **Step 1: Restart backend** (if needed)

```bash
cd medical-backend && mvn spring-boot:run
```

- [ ] **Step 2: Verify recommendation history API**

```bash
curl -s "http://localhost:8080/api/recommendations?patientId=202" \
  -H "Authorization: Bearer <token>"
```
Expected: JSON array of recommendation records for patient 202

- [ ] **Step 3: Verify clinical metrics API**

```bash
curl -s -X PUT "http://localhost:8080/api/patients/202/clinical" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"renalFunction":"normal","smokingStatus":"never"}'
```
Expected: `{"success":true}`

- [ ] **Step 4: Test in browser**

Navigate to `http://localhost:5173/patients`, expand a patient card, verify:
- Three tabs visible: 基本信息 / 推荐记录 / 临床指标
- "推荐记录" tab shows history (or "暂无推荐记录" for new patients)
- "临床指标" tab shows editable form
- Save button persists data

- [ ] **Step 5: Verify DP warning disappears**

After filling clinical metrics, go to `http://localhost:5173/recommendation`, select that patient, verify the "数据缺失" warning no longer shows the fields you filled in.
