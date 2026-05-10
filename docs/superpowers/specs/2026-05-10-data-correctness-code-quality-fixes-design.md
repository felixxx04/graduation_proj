# 数据正确性与代码质量修复 — 设计文档

> 日期：2026-05-10
> 状态：已确认

## 目标

修复代码审查中发现的 MEDIUM 级别数据正确性风险（A1-A4）和 LOW 级别代码质量问题（B1-B5）。

---

## A 类：数据正确性

### A1 — recommendation_id 类型统一（MEDIUM）

**问题：** `review_log.recommendation_id` 为 `VARCHAR(32)`，`recommendation.id` 为 `BIGINT`。JOIN 时 MySQL 隐式转换导致全表扫描。

**修复：**

1. 迁移脚本 `migration_v2_1_type_fix.sql`：
```sql
-- 校验已有数据可转换
SELECT recommendation_id FROM review_log WHERE recommendation_id NOT REGEXP '^[0-9]+$';
-- 改列类型
ALTER TABLE review_log MODIFY COLUMN recommendation_id BIGINT;
ALTER TABLE review_log ADD CONSTRAINT fk_review_recommendation FOREIGN KEY (recommendation_id) REFERENCES recommendation(id);
```

2. 更新 `review_log.sql` 的 CREATE TABLE 定义
3. `ReviewLog.java`: `recommendationId` 从 `String` → `Long`
4. `ReviewLogRepository.java`: `findByRecommendationId()` 和 `updateRecommendationStatus()` 参数从 `String` → `Long`
5. `ReviewController.java`: `@PathVariable String recommendationId` → `@PathVariable Long recommendationId`
6. `ReviewDashboard.tsx`: `PendingReview.recommendationId` 从 `string` → `number`

### A2 — 审核查询加医生过滤（MEDIUM）

**问题：** 审核记录查询未限制医生范围，任何 doctor 可查看所有 doctor 的审核记录。

**修复：**

1. `ReviewController.submitReview()`: 从 SecurityContext 提取当前用户 ID → `log.setDoctorId()`
2. `ReviewLogRepository.java` 新增方法/修改查询，增加 `doctorId` 参数：
   - `findPending()` → `findPendingByDoctorId(Long doctorId)` 或 admin 调用 `findPending()`（全量）
   - `getRejectionStats()`、`getModificationStats()` 同理
3. `ReviewController` 各端点：判断角色，admin → 全量查询，doctor → 仅查自己的

### A3 — 提取共享 getCurrentUserId（MEDIUM）

**问题：** 同一逻辑在 `RecommendationController` 和 `RecommendationService` 中各有一份实现，行为不一致（Controller 返回 null，Service 抛异常）。

**修复：**

1. 新建 `SecurityUtils.java`:
```java
@Component
public class SecurityUtils {
    private final UserRepository userRepository;
    
    public Long getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未认证");
        }
        return userRepository.findByUsername(auth.getName())
            .orElseThrow(() -> new IllegalStateException("认证用户不存在"))
            .getId();
    }
}
```

2. `RecommendationController` 和 `RecommendationService` 注入 `SecurityUtils`，删除各自的 `getCurrentUserId()`

### A4 — submitReview 输入校验（MEDIUM）

**问题：** `submitReview()` 无任何参数校验，空 decision 静默默认为 rejected。

**修复：**

`ReviewController.submitReview()` 开头加：
```java
if (log.getRecommendationId() == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "推荐ID不能为空");
if (log.getDoctorDecision() == null || !List.of("confirm", "modify", "reject").contains(log.getDoctorDecision()))
    throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "审核决策无效，必须为confirm/modify/reject");
```

---

## B 类：代码质量

### B1+B2 — DrugRecommendation.tsx 拆分（LOW）

**问题：** 文件 1381 行（上限 800），`handleAnalyze` 函数 80 行（上限 50）。

**修复：**
- 提取 `SafetyBadge` 组件 → `src/components/SafetyBadge.tsx`
- 提取知情同意弹窗 → `src/components/ConsentDialog.tsx`
- 提取隐私面板 → `src/components/PrivacyPanel.tsx`
- 提取 DP 对比区块 → `src/components/DPComparison.tsx`
- `handleAnalyze` 拆分为 `buildRequest`、`mapResponse`、`handleAnalyzeError` 三个子函数

### B3 — STATUS_CONFIG 颜色常量去重（LOW）

**问题：** 审核状态颜色在 `MyRecords.tsx`、`ReviewDashboard.tsx`、`RecommendationStats.tsx` 三处重复。

**修复：**
- 新建 `src/lib/statusConstants.ts`:
```typescript
export const REVIEW_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending:   { label: '待审核', color: '#888', bg: '#1a1a2e' },
  confirmed: { label: '已确认', color: '#22c55e', bg: '#052e16' },
  modified:  { label: '已修改', color: '#60a5fa', bg: '#1e3a5f' },
  rejected:  { label: '已拒绝', color: '#f87171', bg: '#450a0a' },
}
```
- 三个页面统一 import

### B4 — console.warn 替换（LOW）

**问题：** `DrugRecommendation.tsx` 中 `console.warn` 违反项目规范。

**修复：** 静默忽略或替换为生产级日志（此项目无日志基础设施，直接静默 catch）

### B5 — ReviewPanel 模板切换保护（LOW）

**问题：** 选择模板会静默覆盖用户手动编辑的诊疗建议。

**修复：** 仅在 textarea 为空时自动填充模板文本；若用户已编辑，切换模板时保留文本。

---

## 文件改动清单

### 数据库
| 文件 | 操作 |
|------|------|
| `medical-backend/sql/migration_v2_1_type_fix.sql` | 新建 |
| `medical-backend/sql/review_log.sql` | 修改 |

### 后端
| 文件 | 操作 |
|------|------|
| `.../security/SecurityUtils.java` | 新建 |
| `.../entity/ReviewLog.java` | 修改（recommendationId 类型） |
| `.../repository/ReviewLogRepository.java` | 修改（参数类型 + 医生过滤） |
| `.../controller/ReviewController.java` | 修改（类型 + 校验 + 过滤） |
| `.../controller/RecommendationController.java` | 修改（注入 SecurityUtils） |
| `.../service/RecommendationService.java` | 修改（注入 SecurityUtils） |

### 前端
| 文件 | 操作 |
|------|------|
| `src/lib/statusConstants.ts` | 新建 |
| `src/components/SafetyBadge.tsx` | 新建 |
| `src/components/ConsentDialog.tsx` | 新建 |
| `src/components/PrivacyPanel.tsx` | 新建 |
| `src/components/DPComparison.tsx` | 新建 |
| `src/pages/DrugRecommendation.tsx` | 修改（拆分组件 + 移除 console.warn） |
| `src/pages/MyRecords.tsx` | 修改（导入 statusConstants） |
| `src/pages/ReviewDashboard.tsx` | 修改（类型 + 导入 statusConstants） |
| `src/pages/RecommendationStats.tsx` | 修改（导入 statusConstants） |
| `src/components/ReviewPanel.tsx` | 修改（模板切换保护） |
