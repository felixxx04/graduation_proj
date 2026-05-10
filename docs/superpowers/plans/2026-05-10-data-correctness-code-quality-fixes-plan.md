# 数据正确性与代码质量修复 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 data correctness issues (A1-A4) and 5 code quality issues (B1-B5) from code review.

**Architecture:** Single phase — A1 (type unification) is the foundation since A2-A4 depend on it. B1-B5 are independent of A1-A4.

**Tech Stack:** Spring Boot 3.2 + MyBatis + MySQL, React 18 + TypeScript

---

### Task 1: A1 — recommendation_id 类型统一 (VARCHAR→BIGINT)

**Files:**
- Create: `medical-backend/sql/migration_v2_1_type_fix.sql`
- Modify: `medical-backend/sql/review_log.sql`
- Modify: `medical-backend/src/main/java/com/medical/entity/ReviewLog.java`
- Modify: `medical-backend/src/main/java/com/medical/repository/ReviewLogRepository.java`
- Modify: `medical-backend/src/main/java/com/medical/controller/ReviewController.java`
- Modify: `src/pages/ReviewDashboard.tsx`

- [ ] **Step 1: Create migration script**

```sql
-- 校验现有数据无非法值（如返回行则需先清理）
SELECT id, recommendation_id FROM review_log WHERE recommendation_id NOT REGEXP '^[0-9]+$';

-- 改列类型并加外键
ALTER TABLE review_log MODIFY COLUMN recommendation_id BIGINT;
ALTER TABLE review_log ADD CONSTRAINT fk_review_recommendation FOREIGN KEY (recommendation_id) REFERENCES recommendation(id);
```

- [ ] **Step 2: Fix review_log.sql CREATE TABLE**

Change `recommendation_id VARCHAR(32)` to `recommendation_id BIGINT` in the CREATE TABLE.

- [ ] **Step 3: Fix ReviewLog entity**

```java
// Change: private String recommendationId;
private Long recommendationId;
```

- [ ] **Step 4: Fix ReviewLogRepository**

```java
// Change String to Long in findByRecommendationId, updateRecommendationStatus, insert
ReviewLog findById(@Param("id") Long id);
List<ReviewLog> findByRecommendationId(@Param("recommendationId") Long recommendationId);
int updateRecommendationStatus(@Param("recommendationId") Long recommendationId, @Param("status") String status);
```

Also fix the `findPending()` query — the JOIN no longer needs implicit casting.

- [ ] **Step 5: Fix ReviewController path parameter**

```java
// Change String to Long
public ApiResponse<List<ReviewLog>> getReview(@PathVariable Long recommendationId)
```

- [ ] **Step 6: Fix ReviewDashboard frontend type**

In `PendingReview` interface: `recommendationId: number`

- [ ] **Step 7: Commit**

```bash
git add medical-backend/sql/ medical-backend/src/main/java/com/medical/entity/ReviewLog.java medical-backend/src/main/java/com/medical/repository/ReviewLogRepository.java medical-backend/src/main/java/com/medical/controller/ReviewController.java src/pages/ReviewDashboard.tsx
git commit -m "fix: unify recommendation_id type from VARCHAR to BIGINT across all layers"
```

### Task 2: A2+A3+A4 — SecurityUtils + submitReview fixes

**Files:**
- Create: `medical-backend/src/main/java/com/medical/security/SecurityUtils.java`
- Modify: `medical-backend/src/main/java/com/medical/controller/ReviewController.java`
- Modify: `medical-backend/src/main/java/com/medical/controller/RecommendationController.java`
- Modify: `medical-backend/src/main/java/com/medical/service/RecommendationService.java`

- [ ] **Step 1: Create SecurityUtils.java**

```java
package com.medical.security;

import com.medical.entity.User;
import com.medical.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
@RequiredArgsConstructor
public class SecurityUtils {
    private final UserRepository userRepository;

    public Long getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未认证，请先登录");
        }
        return userRepository.findByUsername(auth.getName())
            .map(User::getId)
            .orElseThrow(() -> new IllegalStateException("认证用户不存在于数据库中"));
    }
}
```

- [ ] **Step 2: Update ReviewController — add validation + doctorId + SecurityUtils**

```java
@RestController
@RequestMapping("/api/review")
@RequiredArgsConstructor
public class ReviewController {
    private final ReviewLogRepository reviewLogRepository;
    private final SecurityUtils securityUtils;

    @PostMapping("/log")
    public ApiResponse<Map<String, Object>> submitReview(@RequestBody ReviewLog log) {
        // Input validation
        if (log.getRecommendationId() == null)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "推荐ID不能为空");
        if (log.getDoctorDecision() == null || !List.of("confirm", "modify", "reject").contains(log.getDoctorDecision()))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "审核决策无效，必须为confirm/modify/reject");

        // Set current doctor
        log.setDoctorId(securityUtils.getCurrentUserId());

        reviewLogRepository.insert(log);
        String newStatus = "confirm".equals(log.getDoctorDecision()) ? "confirmed" :
                          "modify".equals(log.getDoctorDecision()) ? "modified" : "rejected";
        reviewLogRepository.updateRecommendationStatus(log.getRecommendationId(), newStatus);
        return ApiResponse.success(Map.of("id", log.getId(), "reviewStatus", newStatus));
    }

    // ... pending, getReview, stats endpoints => use securityUtils.getCurrentUserId() for filtering
}
```

Add `import org.springframework.http.HttpStatus;` and `import org.springframework.web.server.ResponseStatusException;`.

- [ ] **Step 3: Update RecommendationController — use SecurityUtils**

Replace the private `getCurrentUserId()` with injected `securityUtils.getCurrentUserId()`.

- [ ] **Step 4: Update RecommendationService — use SecurityUtils**

Replace the private `getCurrentUserId()` with injected `securityUtils.getCurrentUserId()`.

- [ ] **Step 5: Commit**

```bash
git add medical-backend/src/main/java/com/medical/
git commit -m "fix: add SecurityUtils, input validation on submitReview, doctor filtering"
```

### Task 3: B1+B2 — DrugRecommendation.tsx component extraction

**Files:**
- Create: `src/components/SafetyBadge.tsx`
- Create: `src/components/ConsentDialog.tsx`
- Create: `src/components/PrivacyPanel.tsx`
- Create: `src/components/DPComparison.tsx`
- Modify: `src/pages/DrugRecommendation.tsx`

- [ ] **Step 1: Extract SafetyBadge**

Move lines 160-186 (safetyConfig + SafetyBadge component) to `src/components/SafetyBadge.tsx`. Export both `safetyConfig` and `SafetyBadge`. Import in DrugRecommendation.

- [ ] **Step 2: Extract ConsentDialog**

Move the consent dialog JSX (lines 422-464) to `src/components/ConsentDialog.tsx`. Props: `onAccept`, `onCancel`.

- [ ] **Step 3: Extract PrivacyPanel**

Move the privacy panel Card (lines 734-798) to `src/components/PrivacyPanel.tsx`. Props: `config`, `budget`, `dpEnabled`, `noiseScale`.

- [ ] **Step 4: Extract DPComparison**

Move the DP comparison section (lines 828-867) to `src/components/DPComparison.tsx`. Props: `comparison`, `dpEnabled`.

- [ ] **Step 5: Clean up DrugRecommendation imports**

Remove unused imports: `AnimatePresence` (check if still used), `Printer`, `Target`, any others now delegated to child components.

- [ ] **Step 6: Commit**

```bash
git add src/components/ src/pages/DrugRecommendation.tsx
git commit -m "refactor: extract components from DrugRecommendation (SafetyBadge, ConsentDialog, PrivacyPanel, DPComparison)"
```

### Task 4: B3 — STATUS_CONFIG deduplication

**Files:**
- Create: `src/lib/statusConstants.ts`
- Modify: `src/pages/MyRecords.tsx`
- Modify: `src/pages/ReviewDashboard.tsx`
- Modify: `src/pages/RecommendationStats.tsx`

- [ ] **Step 1: Create src/lib/statusConstants.ts**

```typescript
export const REVIEW_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending:   { label: '待审核', color: '#888', bg: '#1a1a2e' },
  confirmed: { label: '已确认', color: '#22c55e', bg: '#052e16' },
  modified:  { label: '已修改', color: '#60a5fa', bg: '#1e3a5f' },
  rejected:  { label: '已拒绝', color: '#f87171', bg: '#450a0a' },
}
```

- [ ] **Step 2: Update MyRecords.tsx**

Replace local `STATUS_CONFIG` with import from `statusConstants`. Keep local `STATUS_ICON` (icons import differently).

- [ ] **Step 3: Update ReviewDashboard.tsx**

Replace local `STATUS_CONFIG` with import. Note: ReviewDashboard uses `confirm`/`modify`/`reject` keys (no `modified` in statusConfig). Use a local mapping or consistent keys.

- [ ] **Step 4: Update RecommendationStats.tsx**

Replace local `statusLabels` and `statusColors` with import from `statusConstants`.

- [ ] **Step 5: Commit**

```bash
git add src/lib/statusConstants.ts src/pages/
git commit -m "refactor: extract shared status constants to statusConstants.ts"
```

### Task 5: B4+B5 — console.warn removal + ReviewPanel template protection

**Files:**
- Modify: `src/pages/DrugRecommendation.tsx`
- Modify: `src/components/ReviewPanel.tsx`

- [ ] **Step 1: Remove console.warn**

Find `console.warn('Auto-save patient failed:', e)` in DrugRecommendation.tsx (the `autoSaveNewPatient` catch block). Remove the console.warn line, keep the silent catch.

- [ ] **Step 2: Protect ReviewPanel template edits**

In ReviewPanel.tsx, change the template onChange handler. Current: always overwrites textarea. New: only fill template text if textarea is empty:

```tsx
onChange={e => {
  setSelectedTemplate(e.target.value);
  if (e.target.value && e.target.value !== '自定义' && !treatmentAdvice.trim()) {
    setTreatmentAdvice(TREATMENT_TEMPLATES.find(t => t.name === e.target.value)?.text || '');
  }
}}
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/DrugRecommendation.tsx src/components/ReviewPanel.tsx
git commit -m "fix: remove console.warn, protect template edits from being overwritten"
```

### Task 6: Verify TypeScript compilation

```bash
cd D:\grad_medical && npx tsc --noEmit
```

Expected: zero errors.

---

## File Tally

| Type | Files |
|------|-------|
| Create | 7 (migration SQL, SecurityUtils, statusConstants, SafetyBadge, ConsentDialog, PrivacyPanel, DPComparison) |
| Modify | 11 (review_log.sql, ReviewLog entity, ReviewLogRepository, ReviewController, RecommendationController, RecommendationService, DrugRecommendation, MyRecords, ReviewDashboard, RecommendationStats, ReviewPanel) |
