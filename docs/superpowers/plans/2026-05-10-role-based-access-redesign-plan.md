# RBAC 三角色重构 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将系统从 admin/doctor/researcher 重构为 admin/doctor/patient 三角色体系，新增医生审核页、患者历史记录、管理员药物数据库和推荐统计页。

**Architecture:** 自上而下四阶段：数据库迁移 → 后端 API 重构 → 前端核心（类型/路由/导航） → 前端页面（新建+修改+删除）。每阶段内部可部分并行，阶段之间有严格依赖。

**Tech Stack:** Spring Boot 3.2 + MyBatis + MySQL, React 18 + TypeScript + Tailwind CSS

---

## 阶段一：数据库迁移

### Task 1: 创建迁移脚本并修改 schema/init_data

**Files:**
- Create: `medical-backend/sql/migration_v2_roles.sql`
- Modify: `medical-backend/sql/schema.sql`
- Modify: `medical-backend/sql/init_data.sql`

- [ ] **Step 1: 创建迁移脚本 migration_v2_roles.sql**

```sql
-- =============================================
-- 迁移脚本：v2 三角色重构 (admin/doctor/patient)
-- 执行方式: mysql -u root -p medical_recommendation < migration_v2_roles.sql
-- =============================================

SET NAMES utf8mb4;
USE medical_recommendation;

-- 1. 删除 researcher 账号（如存在）
DELETE FROM privacy_config WHERE user_id IN (SELECT id FROM sys_user WHERE username = 'researcher1');
DELETE FROM sys_user WHERE username = 'researcher1';

-- 2. 修改 sys_user.role 枚举
ALTER TABLE sys_user MODIFY COLUMN role ENUM('admin', 'doctor', 'patient') DEFAULT 'patient';

-- 3. 将原 doctor1 改为 patient1
UPDATE sys_user SET role = 'patient' WHERE username = 'doctor1';

-- 4. 新增真正的 doctor 账号（密码 admin123 的 BCrypt hash）
INSERT INTO sys_user (username, password_hash, role, enabled) VALUES
('doctor1', '$2a$10$lut2nnnjykVjZ.8lPGoyPuwr9q1LnGVK8tMLJ0tNc20L59nqk1QBm', 'doctor', TRUE);

-- 5. 为新 doctor1 创建隐私配置
INSERT INTO privacy_config (user_id, epsilon, delta, sensitivity, noise_mechanism, application_stage, privacy_budget, budget_used)
SELECT id, 0.1, 0.00001, 1.0, 'laplace', 'model', 10.0, 0.0
FROM sys_user WHERE username = 'doctor1';

-- 6. recommendation 表新增审核状态字段
ALTER TABLE recommendation ADD COLUMN IF NOT EXISTS review_status ENUM('pending', 'confirmed', 'modified', 'rejected') DEFAULT 'pending' COMMENT '审核状态';

-- 7. review_log 表新增诊疗建议字段
ALTER TABLE review_log ADD COLUMN IF NOT EXISTS treatment_advice TEXT COMMENT '医生诊疗建议（自由文本）';
ALTER TABLE review_log ADD COLUMN IF NOT EXISTS treatment_template VARCHAR(50) COMMENT '使用的诊疗模板名称';
```

- [ ] **Step 2: 修改 schema.sql**

在 `sys_user` 表定义中，将行：
```sql
role ENUM('admin', 'doctor', 'researcher') DEFAULT 'doctor' COMMENT '角色',
```
改为：
```sql
role ENUM('admin', 'doctor', 'patient') DEFAULT 'patient' COMMENT '角色',
```

在 `recommendation` 表定义中，在 `result_data` 行之后添加：
```sql
review_status ENUM('pending', 'confirmed', 'modified', 'rejected') DEFAULT 'pending' COMMENT '审核状态',
```

- [ ] **Step 3: 修改 init_data.sql**

将：
```sql
('doctor1', '$2a$10$lut2nnnjykVjZ.8lPGoyPuwr9q1LnGVK8tMLJ0tNc20L59nqk1QBm', 'doctor', TRUE),
('researcher1', '$2a$10$lut2nnnjykVjZ.8lPGoyPuwr9q1LnGVK8tMLJ0tNc20L59nqk1QBm', 'researcher', TRUE);
```
改为：
```sql
('patient1', '$2a$10$lut2nnnjykVjZ.8lPGoyPuwr9q1LnGVK8tMLJ0tNc20L59nqk1QBm', 'patient', TRUE),
('doctor1', '$2a$10$lut2nnnjykVjZ.8lPGoyPuwr9q1LnGVK8tMLJ0tNc20L59nqk1QBm', 'doctor', TRUE);
```

- [ ] **Step 4: Commit**

```bash
git add medical-backend/sql/migration_v2_roles.sql medical-backend/sql/schema.sql medical-backend/sql/init_data.sql
git commit -m "feat: add v2 role migration - admin/doctor/patient three-role system"
```

---

## 阶段二：后端 API 重构

### Task 2: 修改 SecurityConfig 角色权限

**Files:**
- Modify: `medical-backend/src/main/java/com/medical/config/SecurityConfig.java`

- [ ] **Step 1: 修改 SecurityConfig.java 的 authorizeHttpRequests 部分**

将整个 `authorizeHttpRequests` lambda 替换为：

```java
.authorizeHttpRequests(auth -> auth
    .requestMatchers("/api/auth/**").permitAll()
    .requestMatchers("/api/health").permitAll()
    .requestMatchers("/api/admin/**").hasRole("ADMIN")
    .requestMatchers("/api/patients/**").hasAnyRole("ADMIN", "DOCTOR")
    .requestMatchers("/api/recommendations/**").authenticated()
    .requestMatchers("/api/review/**").hasAnyRole("DOCTOR", "ADMIN")
    .requestMatchers("/api/privacy/**").hasRole("ADMIN")
    .requestMatchers("/api/drugs/**").hasAnyRole("ADMIN", "DOCTOR")
    .requestMatchers("/api/dashboard/**").hasAnyRole("ADMIN", "DOCTOR")
    .anyRequest().authenticated()
)
```

- [ ] **Step 2: 验证编译**

```bash
cd medical-backend && mvn compile -q
```

- [ ] **Step 3: Commit**

```bash
git add medical-backend/src/main/java/com/medical/config/SecurityConfig.java
git commit -m "feat: update SecurityConfig for three-role system (admin/doctor/patient)"
```

### Task 3: 修改 ReviewLog 实体新增诊疗建议字段

**Files:**
- Modify: `medical-backend/src/main/java/com/medical/entity/ReviewLog.java`

- [ ] **Step 1: 添加两个新字段**

在 `doctorReason` 字段后添加：

```java
private String treatmentAdvice;
private String treatmentTemplate;
```

完整实体文件（新增两行在 doctorReason 之后）：

```java
package com.medical.entity;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ReviewLog {
    private Long id;
    private String recommendationId;
    private Long patientId;
    private String diseaseCn;
    private String diseaseStandardized;
    private String routingPath;
    private String systemDrugs;
    private String doctorDecision;
    private String doctorSelectedDrug;
    private String doctorReason;
    private String treatmentAdvice;
    private String treatmentTemplate;
    private Long doctorId;
    private LocalDateTime createdAt;
}
```

- [ ] **Step 2: 验证编译**

```bash
cd medical-backend && mvn compile -q
```

- [ ] **Step 3: Commit**

```bash
git add medical-backend/src/main/java/com/medical/entity/ReviewLog.java
git commit -m "feat: add treatment_advice and treatment_template fields to ReviewLog"
```

### Task 4: 修改 RecommendationService — 新推荐默认 pending 状态

**Files:**
- Modify: `medical-backend/src/main/java/com/medical/service/RecommendationService.java`
- Modify: `medical-backend/src/main/java/com/medical/entity/Recommendation.java`

- [ ] **Step 1: 在 Recommendation 实体中添加 reviewStatus 字段**

Read `Recommendation.java` first. Add after `recommendationType`:

```java
private String reviewStatus;
```

- [ ] **Step 2: 在 saveRecommendation 方法中设置默认值**

在 `saveRecommendation` 方法中，`recommendation.setRecommendationType("realtime")` 之后添加：

```java
recommendation.setReviewStatus("pending");
```

- [ ] **Step 3: 验证编译**

```bash
cd medical-backend && mvn compile -q
```

- [ ] **Step 4: Commit**

```bash
git add medical-backend/src/main/java/com/medical/entity/Recommendation.java medical-backend/src/main/java/com/medical/service/RecommendationService.java
git commit -m "feat: set review_status='pending' on new recommendations"
```

### Task 5: 新增 API 端点

**Files:**
- Modify: `medical-backend/src/main/java/com/medical/controller/RecommendationController.java`
- Modify: `medical-backend/src/main/java/com/medical/controller/ReviewController.java`
- Modify: `medical-backend/src/main/java/com/medical/controller/DrugController.java`
- Create: `medical-backend/src/main/java/com/medical/controller/StatsController.java`

- [ ] **Step 1: RecommendationController — 新增 my-history 端点**

在 `RecommendationController` 中添加：

```java
@GetMapping("/my-history")
public ApiResponse<List<RecommendationHistoryItem>> getMyHistory() {
    Long userId = getCurrentUserId();
    return ApiResponse.success(recommendationService.getHistoryByUserId(userId));
}
```

需要在 controller 中注入并实现 `getCurrentUserId()`（从 SecurityContextHolder 获取当前用户ID，与 RecommendationService 中的逻辑相同）。

- [ ] **Step 2: RecommendationService — 新增 getHistoryByUserId**

在 `RecommendationService` 中添加：

```java
public List<RecommendationHistoryItem> getHistoryByUserId(Long userId) {
    List<Recommendation> records = recommendationRepository.findByUserId(userId);
    return records.stream().map(this::toHistoryItem).collect(Collectors.toList());
}
```

在 `RecommendationRepository` 中添加（如不存在）：

```java
List<Recommendation> findByUserId(Long userId);
```

在 `toHistoryItem` 方法中添加 `reviewStatus`：

```java
.reviewStatus(rec.getReviewStatus())
```

更新 `RecommendationHistoryItem` DTO 添加 `reviewStatus` 字段：

```java
private String reviewStatus;
```

- [ ] **Step 3: ReviewController — 新增 pending 端点**

在 `ReviewController` 中添加：

```java
@GetMapping("/pending")
public ApiResponse<List<ReviewLog>> getPendingReviews() {
    List<ReviewLog> pending = reviewLogRepository.findPending();
    return ApiResponse.success(pending);
}
```

在 `ReviewLogRepository` 中添加方法。需要在对应的 MyBatis XML mapper 中添加 SQL：

```xml
<select id="findPending" resultType="com.medical.entity.ReviewLog">
    SELECT rl.* FROM review_log rl
    JOIN recommendation r ON rl.recommendation_id = r.id
    WHERE r.review_status = 'pending'
    ORDER BY rl.created_at DESC
</select>
```

- [ ] **Step 4: ReviewController — 保存诊疗建议**

修改 `submitReview` 方法，在保存 review_log 后同步更新 recommendation 的 review_status：

```java
@PostMapping("/log")
public ApiResponse<Map<String, Object>> submitReview(@RequestBody ReviewLog log) {
    reviewLogRepository.insert(log);
    // 同步更新 recommendation 的审核状态
    String decision = log.getDoctorDecision();
    String newStatus = decision.equals("confirm") ? "confirmed" :
                       decision.equals("modify") ? "modified" : "rejected";
    reviewLogRepository.updateRecommendationStatus(log.getRecommendationId(), newStatus);
    Map<String, Object> resp = Map.of("id", log.getId());
    return ApiResponse.success(resp);
}
```

在 `ReviewLogRepository` 的 MyBatis XML mapper 中添加：

```xml
<update id="updateRecommendationStatus">
    UPDATE recommendation SET review_status = #{status} WHERE id = #{recommendationId}
</update>
```

- [ ] **Step 5: DrugController — 新增 database 端点**

在 `DrugController` 中添加：

```java
@GetMapping("/database")
public ApiResponse<List<Drug>> getDrugDatabase(
        @RequestParam(required = false) String search,
        @RequestParam(required = false) String category,
        @RequestParam(required = false) String indication) {
    if (search != null && !search.isBlank()) {
        return ApiResponse.success(drugService.searchDrugs(search));
    }
    if (category != null && !category.isBlank()) {
        return ApiResponse.success(drugService.getDrugsByCategory(category));
    }
    return ApiResponse.success(drugService.getAllDrugs());
}
```

- [ ] **Step 6: 创建 StatsController**

```java
package com.medical.controller;

import com.medical.dto.response.ApiResponse;
import com.medical.repository.RecommendationRepository;
import com.medical.repository.ReviewLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {
    private final RecommendationRepository recommendationRepository;
    private final ReviewLogRepository reviewLogRepository;

    @GetMapping("/recommendations")
    public ApiResponse<Map<String, Object>> getRecommendationStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalRecommendations", recommendationRepository.count());
        stats.put("statusDistribution", recommendationRepository.countByStatus());
        return ApiResponse.success(stats);
    }
}
```

- [ ] **Step 7: 验证编译**

```bash
cd medical-backend && mvn compile -q
```

- [ ] **Step 8: Commit**

```bash
git add medical-backend/src/main/java/com/medical/
git commit -m "feat: add my-history, pending review, drug database, and stats API endpoints"
```

---

## 阶段三：前端核心改造

### Task 6: 重写类型系统（authStore + permissions）

**Files:**
- Modify: `src/lib/authStore.tsx`
- Modify: `src/lib/permissions.ts`

- [ ] **Step 1: 修改 authStore.tsx 类型定义**

`UserRole` 类型改为：
```typescript
export type UserRole = 'admin' | 'doctor' | 'patient'
```

`normalizeUser` 函数改为（删除 researcher 映射）：
```typescript
function normalizeUser(user: BackendUser): AuthUser {
  return {
    id: user.id,
    username: user.username,
    role: (user.role === 'admin' || user.role === 'doctor' || user.role === 'patient')
      ? user.role as UserRole
      : 'patient',
    status: user.status,
  }
}
```

- [ ] **Step 2: 重写 permissions.ts**

```typescript
import type { UserRole } from '@/lib/authStore'

export type AppFeature =
  | 'recommendation'
  | 'my_records'
  | 'patients'
  | 'review'
  | 'drug_database'
  | 'recommendation_stats'
  | 'privacy'
  | 'admin'

export const FEATURE_LABEL: Record<AppFeature, string> = {
  recommendation: '用药推荐',
  my_records: '我的记录',
  patients: '患者档案',
  review: '推荐审核',
  drug_database: '药物数据库',
  recommendation_stats: '推荐统计',
  privacy: '隐私配置',
  admin: '后台管理',
}

export const ROLE_FEATURES: Record<UserRole, AppFeature[]> = {
  patient: ['recommendation', 'my_records'],
  doctor: ['patients', 'review'],
  admin: ['patients', 'review', 'drug_database', 'recommendation_stats', 'privacy', 'admin'],
}

export function canAccessFeature(role: UserRole | undefined, feature: AppFeature) {
  if (!role) return false
  return ROLE_FEATURES[role].includes(feature)
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add src/lib/authStore.tsx src/lib/permissions.ts
git commit -m "refactor: update UserRole to admin/doctor/patient, rewrite permissions matrix"
```

### Task 7: 修改 AuthGuards — RequireRole 支持"或"逻辑

**Files:**
- Modify: `src/components/AuthGuards.tsx`

- [ ] **Step 1: 修改 RequireRole 支持多角色**

将 `RequireRole` 改为接受 `role` 或 `roles` 数组：

```tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth, type UserRole } from '@/lib/authStore'

function AuthLoading() {
  return <div className="py-16 text-center text-sm text-muted-foreground">正在验证登录状态...</div>
}

export function RequireAuth() {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()

  if (isInitializing) return <AuthLoading />
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

export function RequireAuthModal() {
  const { isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()

  if (isInitializing) return <AuthLoading />
  if (!isAuthenticated) return <Navigate to="/" replace state={{ loginModal: true, from: location.pathname }} />
  return <Outlet />
}

export function RequireRole({ role, roles }: { role?: UserRole; roles?: UserRole[] }) {
  const { user, isInitializing } = useAuth()
  const location = useLocation()
  const allowedRoles = roles || (role ? [role] : [])

  if (isInitializing) return <AuthLoading />
  if (!user) return <Navigate to="/" replace state={{ loginModal: true, from: location.pathname }} />
  if (!allowedRoles.includes(user.role)) return <Navigate to="/forbidden" replace />
  return <Outlet />
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add src/components/AuthGuards.tsx
git commit -m "refactor: RequireRole supports multiple roles via 'roles' prop"
```

### Task 8: 重构路由（App.tsx）

**Files:**
- Modify: `src/App.tsx`

- [ ] **Step 1: 重写 App.tsx 路由结构**

```tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import PatientRecords from './pages/PatientRecords'
import PrivacyConfig from './pages/PrivacyConfig'
import DrugRecommendation from './pages/DrugRecommendation'
import LoginPage from './pages/LoginPage'
import ForbiddenPage from './pages/ForbiddenPage'
import AdminDashboard from './pages/AdminDashboard'
import MyRecords from './pages/MyRecords'
import ReviewDashboard from './pages/ReviewDashboard'
import DrugDatabase from './pages/DrugDatabase'
import RecommendationStats from './pages/RecommendationStats'
import { RequireAuthModal, RequireRole } from './components/AuthGuards'

function App() {
  return (
    <Router>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forbidden" element={<ForbiddenPage />} />

        {/* App shell is public */}
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />

          {/* Patient: any authenticated user can access recommendation and my-records */}
          <Route element={<RequireAuthModal />}>
            <Route path="recommendation/*" element={<DrugRecommendation />} />
            <Route path="my-records/*" element={<MyRecords />} />
          </Route>

          {/* Doctor + Admin */}
          <Route element={<RequireRole roles={['doctor', 'admin']} />}>
            <Route path="patients/*" element={<PatientRecords />} />
            <Route path="review/*" element={<ReviewDashboard />} />
          </Route>

          {/* Admin only */}
          <Route element={<RequireRole role="admin" />}>
            <Route path="drug-database/*" element={<DrugDatabase />} />
            <Route path="recommendation-stats/*" element={<RecommendationStats />} />
            <Route path="privacy/*" element={<PrivacyConfig />} />
            <Route path="admin/*" element={<AdminDashboard />} />
          </Route>
        </Route>
      </Routes>
    </Router>
  )
}

export default App
```

- [ ] **Step 2: 创建新页面占位文件（Step 1 需要引用这些组件）**

创建四个占位页面文件，每个包含最小可渲染内容：

`src/pages/MyRecords.tsx`:
```tsx
export default function MyRecords() {
  return <div className="p-8"><h1 className="text-2xl font-bold">我的记录</h1><p className="text-muted-foreground mt-2">查看推荐历史和医生诊疗建议</p></div>
}
```

`src/pages/ReviewDashboard.tsx`:
```tsx
export default function ReviewDashboard() {
  return <div className="p-8"><h1 className="text-2xl font-bold">推荐审核</h1><p className="text-muted-foreground mt-2">审核患者的用药推荐</p></div>
}
```

`src/pages/DrugDatabase.tsx`:
```tsx
export default function DrugDatabase() {
  return <div className="p-8"><h1 className="text-2xl font-bold">药物数据库</h1><p className="text-muted-foreground mt-2">浏览系统支持的药物完整临床数据</p></div>
}
```

`src/pages/RecommendationStats.tsx`:
```tsx
export default function RecommendationStats() {
  return <div className="p-8"><h1 className="text-2xl font-bold">推荐统计</h1><p className="text-muted-foreground mt-2">推荐分布统计与隐私预算可视化</p></div>
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add src/App.tsx src/pages/MyRecords.tsx src/pages/ReviewDashboard.tsx src/pages/DrugDatabase.tsx src/pages/RecommendationStats.tsx
git commit -m "feat: restructure routes for three-role system, add placeholder pages"
```

### Task 9: 重构导航栏（Layout.tsx）

**Files:**
- Modify: `src/components/Layout.tsx`

- [ ] **Step 1: 更新 navigation 定义**

将 navigation 数组中的路由和权限改为新体系：

```typescript
const navigation = useMemo(
  () => [
    { name: '首页', href: '/', icon: Activity },
    ...(canAccessFeature(user?.role, 'recommendation') ? [{ name: '用药推荐', href: '/recommendation', icon: Stethoscope }] : []),
    ...(canAccessFeature(user?.role, 'my_records') ? [{ name: '我的记录', href: '/my-records', icon: FileText }] : []),
    ...(canAccessFeature(user?.role, 'patients') ? [{ name: '患者档案', href: '/patients', icon: Users }] : []),
    ...(canAccessFeature(user?.role, 'review') ? [{ name: '推荐审核', href: '/review', icon: Shield }] : []),
    ...(canAccessFeature(user?.role, 'drug_database') ? [{ name: '药物数据库', href: '/drug-database', icon: Pill }] : []),
    ...(canAccessFeature(user?.role, 'recommendation_stats') ? [{ name: '推荐统计', href: '/recommendation-stats', icon: BarChart3 }] : []),
    ...(canAccessFeature(user?.role, 'privacy') ? [{ name: '隐私配置', href: '/privacy', icon: Lock }] : []),
    ...(canAccessFeature(user?.role, 'admin') ? [{ name: '后台管理', href: '/admin', icon: Settings }] : []),
  ],
  [user?.role]
)
```

需要在文件顶部添加缺少的图标 import：`FileText`, `Pill`, `Lock`。

- [ ] **Step 2: 更新角色显示标签**

在桌面和移动端用户信息区域，将角色标签从：
```tsx
{user.role === 'admin' ? '管理员' : user.role === 'doctor' ? '医生' : '研究员'}
```
改为：
```tsx
{user.role === 'admin' ? '管理员' : user.role === 'doctor' ? '医生' : '患者'}
```

- [ ] **Step 3: 更新登录弹窗测试账号提示**

将登录弹窗底部的测试账号提示改为：

```tsx
<div className="grid grid-cols-3 gap-2 pt-1">
  <div className="rounded-md border border-ia-border p-2.5">
    <div className="text-ia-label text-muted-foreground mb-1">患者账号</div>
    <div className="text-ia-caption font-heading font-semibold">patient1</div>
    <div className="text-ia-label text-muted-foreground">admin123</div>
  </div>
  <div className="rounded-md border border-ia-border p-2.5">
    <div className="text-ia-label text-muted-foreground mb-1">医生账号</div>
    <div className="text-ia-caption font-heading font-semibold">doctor1</div>
    <div className="text-ia-label text-muted-foreground">admin123</div>
  </div>
  <div className="rounded-md border border-ia-border p-2.5">
    <div className="text-ia-label text-muted-foreground mb-1">管理员</div>
    <div className="text-ia-caption font-heading font-semibold">admin</div>
    <div className="text-ia-label text-muted-foreground">admin123</div>
  </div>
</div>
```

- [ ] **Step 4: 更新 import 语句**

```typescript
import {
  Activity, Users, Shield, Stethoscope, BarChart3, Settings,
  Menu, X, LogOut, User as UserIcon, LogIn, Lock, Heart, ChevronRight,
  FileText, Pill,
} from 'lucide-react'
```

- [ ] **Step 5: 验证编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 6: Commit**

```bash
git add src/components/Layout.tsx
git commit -m "feat: rebuild navigation for three-role system with new test accounts"
```

---

## 阶段四：前端页面开发

### Task 10: 修改 DrugRecommendation.tsx（患者端只读）

**Files:**
- Modify: `src/pages/DrugRecommendation.tsx`

- [ ] **Step 1: 移除 ReviewPanel import 和渲染**

删除 import：
```typescript
// 删除这一行
import ReviewPanel from '../components/ReviewPanel'
```

删除 ReviewPanel 渲染块（第 1175-1204 行）。

- [ ] **Step 2: 添加审核状态标签组件**

在 `DrugResult` 接口中添加字段：
```typescript
reviewStatus?: 'pending' | 'confirmed' | 'modified' | 'rejected'
```

在药物卡片中，安全标签旁边添加审核状态显示：

```tsx
{rec.reviewStatus && (
  <span style={{
    display: 'inline-block',
    marginLeft: '6px',
    padding: '1px 6px',
    borderRadius: '3px',
    fontSize: '10px',
    fontWeight: 600,
    background:
      rec.reviewStatus === 'confirmed' ? '#052e16' :
      rec.reviewStatus === 'modified' ? '#1e3a5f' :
      rec.reviewStatus === 'rejected' ? '#450a0a' : '#1a1a2e',
    color:
      rec.reviewStatus === 'confirmed' ? '#22c55e' :
      rec.reviewStatus === 'modified' ? '#60a5fa' :
      rec.reviewStatus === 'rejected' ? '#f87171' : '#888',
  }}>
    {rec.reviewStatus === 'pending' ? '待审核' :
     rec.reviewStatus === 'confirmed' ? '已确认' :
     rec.reviewStatus === 'modified' ? '已修改' : '已拒绝'}
  </span>
)}
```

- [ ] **Step 3: 验证编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/DrugRecommendation.tsx
git commit -m "refactor: remove ReviewPanel from patient page, add review status badges"
```

### Task 11: 开发 ReviewDashboard（医生审核页）

**Files:**
- Modify: `src/pages/ReviewDashboard.tsx` (replace placeholder)
- Modify: `src/components/ReviewPanel.tsx` (add template support)

- [ ] **Step 1: 增强 ReviewPanel — 添加诊疗建议模板**

在 ReviewPanel 中添加模板选择。在 `decision` 和 `reason` 之间插入模板选择：

```tsx
const TREATMENT_TEMPLATES = [
  { name: '标准用法', text: '建议使用[药物名]，每日[N]次，每次[剂量]，连用[N]天。' },
  { name: '递增剂量', text: '起始剂量[小剂量]，根据耐受情况逐步调整至[目标剂量]。' },
  { name: '联合用药', text: '建议[药物A]联合[药物B]，注意监测[相互作用/不良反应]。' },
  { name: '对症治疗', text: '针对[症状]进行对症治疗，如症状持续或加重请及时复诊。' },
  { name: '自定义', text: '' },
]
```

在 ReviewPanel 接口中添加：
```typescript
interface ReviewPanelProps {
  recommendationId: string;
  diseaseCn: string;
  drugs: DrugOption[];
  onSubmitReview: (decision: 'confirm' | 'modify' | 'reject', selectedDrug?: string, reason?: string, template?: string, advice?: string) => void;
}
```

在 UI 中，在 reason textarea 之后添加：

```tsx
{decision && (
  <div className="mb-3">
    <label className="block text-xs mb-1" style={{ color: '#888' }}>诊疗建议模板（可选）：</label>
    <select
      value={selectedTemplate}
      onChange={e => { setSelectedTemplate(e.target.value); if (e.target.value && e.target.value !== '自定义') setTreatmentAdvice(TREATMENT_TEMPLATES.find(t => t.name === e.target.value)?.text || '') }}
      className="w-full p-2 rounded-md text-sm mb-2"
      style={{ background: '#0f172a', color: '#ccc', border: '1px solid #333' }}
    >
      <option value="">-- 选择模板 --</option>
      {TREATMENT_TEMPLATES.map(t => (
        <option key={t.name} value={t.name}>{t.name}</option>
      ))}
    </select>
    <label className="block text-xs mb-1" style={{ color: '#888' }}>诊疗建议（可编辑）：</label>
    <textarea
      value={treatmentAdvice}
      onChange={e => setTreatmentAdvice(e.target.value)}
      placeholder="请输入诊疗建议..."
      rows={3}
      className="w-full p-2 rounded-md text-sm resize-y"
      style={{ background: '#0f172a', color: '#ccc', border: '1px solid #333' }}
    />
  </div>
)}
```

添加状态：
```tsx
const [selectedTemplate, setSelectedTemplate] = useState('');
const [treatmentAdvice, setTreatmentAdvice] = useState('');
```

修改 `handleSubmit` 传递新字段：
```tsx
onSubmitReview(decision, selectedDrug || undefined, reason || undefined, selectedTemplate || undefined, treatmentAdvice || undefined);
```

- [ ] **Step 2: 实现 ReviewDashboard 页面**

```tsx
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import ReviewPanel from '../components/ReviewPanel'
import { Shield, Clock, CheckCircle, XCircle, Edit } from 'lucide-react'

interface PendingReview {
  id: number
  recommendationId: string
  patientId: number
  diseaseCn: string
  diseaseStandardized: string
  routingPath: string
  systemDrugs: string
  doctorDecision: string | null
  createdAt: string
}

interface DrugOption {
  drugName: string
  englishName: string
  category: string
  safetyType: string
  score: number
}

export default function ReviewDashboard() {
  const [pendingReviews, setPendingReviews] = useState<PendingReview[]>([])
  const [selectedReview, setSelectedReview] = useState<PendingReview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPending = async () => {
    setLoading(true)
    try {
      const data = await api.get<PendingReview[]>('/api/review/pending')
      setPendingReviews(data)
    } catch {
      setError('获取待审核列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchPending() }, [])

  const handleSubmitReview = async (
    decision: 'confirm' | 'modify' | 'reject',
    selectedDrug?: string,
    reason?: string,
    template?: string,
    advice?: string,
  ) => {
    if (!selectedReview) return
    try {
      await api.post('/api/review/log', {
        recommendationId: selectedReview.recommendationId,
        patientId: selectedReview.patientId,
        diseaseCn: selectedReview.diseaseCn,
        diseaseStandardized: selectedReview.diseaseStandardized,
        routingPath: selectedReview.routingPath,
        systemDrugs: selectedReview.systemDrugs,
        doctorDecision: decision,
        doctorSelectedDrug: selectedDrug || null,
        doctorReason: reason || null,
        treatmentTemplate: template || null,
        treatmentAdvice: advice || null,
      })
      setSelectedReview(null)
      fetchPending()
    } catch {
      setError('提交审核失败')
    }
  }

  const parseDrugs = (systemDrugs: string): DrugOption[] => {
    try { return JSON.parse(systemDrugs) } catch { return [] }
  }

  const statusIcon = (status: string | null) => {
    if (!status || status === 'pending') return <Clock className="h-4 w-4 text-muted-foreground" />
    if (status === 'confirm') return <CheckCircle className="h-4 w-4 text-green-500" />
    if (status === 'modify') return <Edit className="h-4 w-4 text-blue-500" />
    return <XCircle className="h-4 w-4 text-red-500" />
  }

  if (loading) return <div className="p-8 text-center text-muted-foreground">加载中...</div>

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <Shield className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">推荐审核</h1>
            <p className="text-ia-body text-muted-foreground mt-1">审核患者的用药推荐，出具诊疗建议</p>
          </div>
        </div>
      </section>

      {error && (
        <div className="p-3 rounded-sm bg-destructive/6 border border-destructive/30 text-destructive text-sm">{error}</div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-2">
          <h3 className="font-heading font-semibold text-sm text-muted-foreground mb-2">
            待审核 ({pendingReviews.length})
          </h3>
          {pendingReviews.length === 0 && (
            <p className="text-sm text-muted-foreground">暂无待审核推荐</p>
          )}
          {pendingReviews.map(review => (
            <div
              key={review.id}
              onClick={() => setSelectedReview(review)}
              className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                selectedReview?.id === review.id
                  ? 'border-brand-sky bg-brand-sky/5'
                  : 'border-white/[0.06] bg-surface hover:bg-surface-elevated'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-heading font-semibold text-sm">{review.diseaseCn}</span>
                  {review.diseaseStandardized && (
                    <span className="text-xs text-muted-foreground ml-2">→ {review.diseaseStandardized}</span>
                  )}
                </div>
                {statusIcon(review.doctorDecision)}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {new Date(review.createdAt).toLocaleDateString('zh-CN')}
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2">
          {selectedReview ? (
            <Card hover="none">
              <CardHeader>
                <CardTitle className="text-base">审核详情</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                  <div className="text-sm text-muted-foreground">患者症状</div>
                  <div className="font-heading font-semibold mt-1">{selectedReview.diseaseCn}</div>
                  {selectedReview.routingPath && (
                    <>
                      <div className="text-sm text-muted-foreground mt-3">路由路径</div>
                      <div className="text-xs mt-1" style={{ color: '#00d4aa' }}>{selectedReview.routingPath}</div>
                    </>
                  )}
                </div>

                <ReviewPanel
                  recommendationId={selectedReview.recommendationId}
                  diseaseCn={selectedReview.diseaseCn}
                  drugs={parseDrugs(selectedReview.systemDrugs)}
                  onSubmitReview={handleSubmitReview}
                />
              </CardContent>
            </Card>
          ) : (
            <div className="p-8 text-center text-muted-foreground border border-dashed border-white/[0.06] rounded-lg">
              选择左侧待审核记录查看详情
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/ReviewDashboard.tsx src/components/ReviewPanel.tsx
git commit -m "feat: implement doctor review dashboard with treatment advice templates"
```

### Task 12: 开发 MyRecords（患者推荐历史）

**Files:**
- Modify: `src/pages/MyRecords.tsx` (replace placeholder)

- [ ] **Step 1: 实现 MyRecords 页面**

```tsx
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { Clock, CheckCircle, XCircle, Edit, FileText, ChevronDown, ChevronUp } from 'lucide-react'

interface HistoryItem {
  id: number
  patientId: number | null
  recommendedDrugs: string[]
  primaryDisease: string
  dpEnabled: boolean
  epsilonUsed: number | null
  reviewStatus: string | null
  createdAt: string
}

export default function MyRecords() {
  const [records, setRecords] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    const fetchRecords = async () => {
      try {
        const data = await api.get<HistoryItem[]>('/api/recommendations/my-history')
        setRecords(data)
      } catch { /* silent */ }
      finally { setLoading(false) }
    }
    fetchRecords()
  }, [])

  const statusBadge = (status: string | null) => {
    const config: Record<string, { label: string; color: string; bg: string; icon: JSX.Element }> = {
      pending:   { label: '待审核', color: '#888', bg: '#1a1a2e', icon: <Clock className="h-3.5 w-3.5" /> },
      confirmed: { label: '已确认', color: '#22c55e', bg: '#052e16', icon: <CheckCircle className="h-3.5 w-3.5" /> },
      modified:  { label: '已修改', color: '#60a5fa', bg: '#1e3a5f', icon: <Edit className="h-3.5 w-3.5" /> },
      rejected:  { label: '已拒绝', color: '#f87171', bg: '#450a0a', icon: <XCircle className="h-3.5 w-3.5" /> },
    }
    const c = config[status || 'pending'] || config.pending
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '1px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 600, color: c.color, background: c.bg }}>
        {c.icon} {c.label}
      </span>
    )
  }

  if (loading) return <div className="p-8 text-center text-muted-foreground">加载中...</div>

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">我的记录</h1>
            <p className="text-ia-body text-muted-foreground mt-1">查看推荐历史和医生诊疗建议</p>
          </div>
        </div>
      </section>

      {records.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground border border-dashed border-white/[0.06] rounded-lg">
          暂无推荐记录
        </div>
      ) : (
        <div className="space-y-3">
          {records.map(record => (
            <Card key={record.id} hover="none">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div>
                      <div className="font-heading font-semibold">{record.primaryDisease || '未知疾病'}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {new Date(record.createdAt).toLocaleString('zh-CN')}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {statusBadge(record.reviewStatus)}
                    <button
                      onClick={() => setExpandedId(expandedId === record.id ? null : record.id)}
                      className="p-1 rounded hover:bg-surface"
                    >
                      {expandedId === record.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                {expandedId === record.id && (
                  <div className="mt-3 pt-3 border-t border-white/[0.06]">
                    <div className="text-sm text-muted-foreground mb-1">推荐药物：</div>
                    <div className="flex flex-wrap gap-1.5">
                      {record.recommendedDrugs.map((drug, i) => (
                        <span key={i} className="ia-badge ia-badge-primary">{drug}</span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/MyRecords.tsx
git commit -m "feat: implement patient recommendation history page"
```

### Task 13: 开发 DrugDatabase（管理员药物数据库）

**Files:**
- Modify: `src/pages/DrugDatabase.tsx` (replace placeholder)

- [ ] **Step 1: 实现 DrugDatabase 页面**

```tsx
import { useEffect, useState, useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import { Search, Pill, ChevronDown, ChevronUp } from 'lucide-react'

interface Drug {
  id: number
  name: string
  genericName: string
  category: string
  indications: any
  contraindications: any
  sideEffects: any
  interactions: any
  pregnancyCategory: string
  typicalDosage: string
  typicalFrequency: string
  description: string
}

export default function DrugDatabase() {
  const [drugs, setDrugs] = useState<Drug[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    const fetchDrugs = async () => {
      try {
        const data = await api.get<Drug[]>('/api/drugs')
        setDrugs(data)
      } catch { /* silent */ }
      finally { setLoading(false) }
    }
    fetchDrugs()
  }, [])

  const categories = useMemo(() => [...new Set(drugs.map(d => d.category).filter(Boolean))].sort(), [drugs])

  const filtered = useMemo(() => {
    return drugs.filter(d => {
      if (search && !d.name.includes(search) && !(d.genericName || '').includes(search)) return false
      if (categoryFilter && d.category !== categoryFilter) return false
      return true
    })
  }, [drugs, search, categoryFilter])

  const parseList = (val: any): string[] => {
    if (!val) return []
    if (Array.isArray(val)) return val.map(v => typeof v === 'string' ? v : JSON.stringify(v))
    if (typeof val === 'string') {
      try { return JSON.parse(val) } catch { return [val] }
    }
    return []
  }

  if (loading) return <div className="p-8 text-center text-muted-foreground">加载中...</div>

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <Pill className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">药物数据库</h1>
            <p className="text-ia-body text-muted-foreground mt-1">浏览系统支持的 {drugs.length} 种药物完整临床数据</p>
          </div>
        </div>
      </section>

      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="搜索药物名称..."
            className="pl-9"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
          className="h-10 rounded-sm border border-white/[0.06] bg-surface-elevated px-3 text-sm"
        >
          <option value="">所有分类 ({categories.length})</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="text-sm text-muted-foreground">共 {filtered.length} 种药物</div>

      <div className="space-y-2">
        {filtered.slice(0, 100).map(drug => (
          <Card key={drug.id} hover="none">
            <CardContent className="p-4">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedId(expandedId === drug.id ? null : drug.id)}
              >
                <div className="flex items-center gap-3">
                  <Pill className="h-4 w-4 text-brand-sky" />
                  <div>
                    <span className="font-heading font-semibold">{drug.name}</span>
                    {drug.genericName && <span className="text-xs text-muted-foreground ml-2">({drug.genericName})</span>}
                  </div>
                  <span className="ia-badge ia-badge-primary text-[10px]">{drug.category}</span>
                </div>
                {expandedId === drug.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </div>

              {expandedId === drug.id && (
                <div className="mt-3 pt-3 border-t border-white/[0.06] grid md:grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-muted-foreground text-xs mb-1">适应症</div>
                    <div className="flex flex-wrap gap-1">
                      {parseList(drug.indications).map((ind, i) => (
                        <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-brand-sky/10 text-brand-sky">{ind}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs mb-1">禁忌症</div>
                    <div className="flex flex-wrap gap-1">
                      {parseList(drug.contraindications).map((c, i) => (
                        <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">{c}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs mb-1">副作用</div>
                    <div className="flex flex-wrap gap-1">
                      {parseList(drug.sideEffects).slice(0, 10).map((se, i) => (
                        <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">{se}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs mb-1">其他信息</div>
                    <div className="text-xs space-y-0.5">
                      {drug.pregnancyCategory && <div>妊娠分级: {drug.pregnancyCategory}</div>}
                      {drug.typicalDosage && <div>常用剂量: {drug.typicalDosage}</div>}
                      {drug.typicalFrequency && <div>用药频率: {drug.typicalFrequency}</div>}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/DrugDatabase.tsx
git commit -m "feat: implement admin drug database page with search and filter"
```

### Task 14: 开发 RecommendationStats（管理员推荐统计）

**Files:**
- Modify: `src/pages/RecommendationStats.tsx` (replace placeholder)

- [ ] **Step 1: 实现 RecommendationStats 页面**

```tsx
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { usePrivacyStore } from '@/lib/privacyStore'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { BarChart3, TrendingUp, Activity, Shield, Search, Sparkles } from 'lucide-react'

export default function RecommendationStats() {
  const { config, budget } = usePrivacyStore()
  const [stats, setStats] = useState<{ totalRecommendations: number; statusDistribution: Record<string, number> } | null>(null)
  const [demoDisease, setDemoDisease] = useState('')
  const [demoResult, setDemoResult] = useState<any>(null)
  const [demoLoading, setDemoLoading] = useState(false)

  useEffect(() => {
    api.get<{ totalRecommendations: number; statusDistribution: Record<string, number> }>('/api/stats/recommendations')
      .then(setStats)
      .catch(() => {})
  }, [])

  const handleDemo = async () => {
    if (!demoDisease.trim()) return
    setDemoLoading(true)
    try {
      const result = await api.post('/api/recommendations/generate', {
        diseases: demoDisease,
        dpEnabled: false,
        topK: 4,
      })
      setDemoResult(result)
    } catch { /* silent */ }
    finally { setDemoLoading(false) }
  }

  const statusData = stats ? Object.entries(stats.statusDistribution).map(([k, v]) => ({
    name: { pending: '待审核', confirmed: '已确认', modified: '已修改', rejected: '已拒绝' }[k] || k,
    value: v,
    color: { pending: '#888', confirmed: '#22c55e', modified: '#60a5fa', rejected: '#f87171' }[k] || '#888',
  })) : []

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">推荐统计</h1>
            <p className="text-ia-body text-muted-foreground mt-1">推荐分布统计与实时路由演示</p>
          </div>
        </div>
      </section>

      {/* Stats Cards */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card hover="none">
          <CardContent className="p-4 text-center">
            <TrendingUp className="h-5 w-5 text-brand-sky mx-auto mb-2" />
            <div className="text-2xl font-heading font-bold">{stats?.totalRecommendations || 0}</div>
            <div className="text-sm text-muted-foreground">总推荐次数</div>
          </CardContent>
        </Card>
        <Card hover="none">
          <CardContent className="p-4 text-center">
            <Activity className="h-5 w-5 text-secondary mx-auto mb-2" />
            <div className="text-2xl font-heading font-bold">{stats?.statusDistribution?.pending || 0}</div>
            <div className="text-sm text-muted-foreground">待审核</div>
          </CardContent>
        </Card>
        <Card hover="none">
          <CardContent className="p-4 text-center">
            <Shield className="h-5 w-5 text-green-500 mx-auto mb-2" />
            <div className="text-2xl font-heading font-bold">
              {budget.remaining.toFixed(1)} / {config.privacyBudget.toFixed(1)}
            </div>
            <div className="text-sm text-muted-foreground">隐私预算剩余</div>
          </CardContent>
        </Card>
      </div>

      {/* Status Distribution Chart */}
      {statusData.length > 0 && (
        <Card hover="none">
          <CardHeader><CardTitle className="text-base">审核状态分布</CardTitle></CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="name" stroke="#888" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#888" tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '4px', fontSize: '12px' }} />
                  <Bar dataKey="value" name="数量">
                    {statusData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Live Demo */}
      <Card hover="none">
        <CardHeader><CardTitle className="text-base">实时路由演示</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-3">
            <Input
              value={demoDisease}
              onChange={e => setDemoDisease(e.target.value)}
              placeholder="输入疾病名，如：高血压、感冒、腹泻..."
              className="flex-1"
            />
            <Button onClick={handleDemo} loading={demoLoading} className="gap-2">
              <Sparkles className="h-4 w-4" /> 演示
            </Button>
          </div>

          {demoResult?.selected && (
            <div className="space-y-2 mt-4">
              {demoResult.selected.map((item: any, i: number) => (
                <div key={i} className="p-3 rounded-sm bg-surface border border-white/[0.06]">
                  <div className="flex items-center gap-2">
                    <span className="font-heading font-semibold">{item.drugName}</span>
                    <span className="ia-badge ia-badge-primary text-[10px]">{item.category}</span>
                    <span className="text-xs text-muted-foreground">score: {item.score?.toFixed(3)}</span>
                  </div>
                  {item.routingPath && (
                    <div className="text-xs mt-1" style={{ color: '#00d4aa' }}>{item.routingPath}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

```bash
npx tsc --noEmit --pretty false 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/RecommendationStats.tsx
git commit -m "feat: implement admin recommendation stats with live routing demo"
```

---

## 阶段五：清理与验证

### Task 15: 删除废弃文件，更新 HomePage

**Files:**
- Delete: `src/pages/PrivacyVisualization.tsx`
- Modify: `src/pages/HomePage.tsx`
- Modify: `src/pages/LoginPage.tsx`

- [ ] **Step 1: 删除 PrivacyVisualization.tsx**

```bash
git rm src/pages/PrivacyVisualization.tsx
```

- [ ] **Step 2: 更新 HomePage 的 CTA 按钮**

Read `HomePage.tsx`，将 CTA 按钮中的权限判断改为新角色体系。将 `canAccessFeature(user?.role, 'visualization')` 替换为 `canAccessFeature(user?.role, 'recommendation_stats')`。如果有 `'患者档案'` 按钮的权限判断，使用的是 `canAccessFeature(user?.role, 'patients')`，保持不变（患者角色自动无权限）。

- [ ] **Step 3: 更新 LoginPage 提示**

Read `LoginPage.tsx`。如果登录页有测试账号提示，改为新三角色的三个账号。

- [ ] **Step 4: Commit**

```bash
git add src/pages/PrivacyVisualization.tsx src/pages/HomePage.tsx src/pages/LoginPage.tsx
git commit -m "chore: remove PrivacyVisualization, update HomePage and LoginPage for three-role system"
```

### Task 16: 端到端验证

**Files:** None (manual testing)

- [ ] **Step 1: 运行数据库迁移**

```bash
mysql -u root -p medical_recommendation < medical-backend/sql/migration_v2_roles.sql
```

验证：`SELECT id, username, role FROM sys_user;` 应显示 admin(admin), doctor1(doctor), patient1(patient)

- [ ] **Step 2: 启动后端并验证编译**

```bash
cd medical-backend && mvn clean compile -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 3: 启动前端并验证编译**

```bash
npx tsc --noEmit
```

Expected: 无错误

- [ ] **Step 4: 验证各角色登录和导航**

手动测试：
- patient1 登录 → 导航栏显示"首页、用药推荐、我的记录"，角色标签"患者"
- doctor1 登录 → 导航栏显示"首页、患者档案、推荐审核"，角色标签"医生"
- admin 登录 → 导航栏显示所有菜单项

- [ ] **Step 5: 验证患者端不显示患者档案**

patient1 登录后，URL 访问 `/patients` → 应跳转到 `/forbidden`

- [ ] **Step 6: 验证医生审核流程**

1. patient1 提交一个推荐（输入疾病如"高血压"）
2. doctor1 登录 → `/review` → 应看到待审核记录
3. doctor1 审核并填写诊疗建议
4. patient1 → `/my-records` → 应看到审核结果

- [ ] **Step 7: Commit any remaining changes**

---

## 文件改动总览

### 数据库
| 文件 | 操作 |
|------|------|
| `medical-backend/sql/migration_v2_roles.sql` | 新建 |
| `medical-backend/sql/schema.sql` | 修改 |
| `medical-backend/sql/init_data.sql` | 修改 |

### 后端
| 文件 | 操作 |
|------|------|
| `.../config/SecurityConfig.java` | 修改 |
| `.../entity/ReviewLog.java` | 修改 |
| `.../entity/Recommendation.java` | 修改 |
| `.../service/RecommendationService.java` | 修改 |
| `.../controller/RecommendationController.java` | 修改 |
| `.../controller/ReviewController.java` | 修改 |
| `.../controller/DrugController.java` | 修改 |
| `.../controller/StatsController.java` | 新建 |

### 前端
| 文件 | 操作 |
|------|------|
| `src/lib/authStore.tsx` | 修改 |
| `src/lib/permissions.ts` | 重写 |
| `src/App.tsx` | 重写 |
| `src/components/AuthGuards.tsx` | 修改 |
| `src/components/Layout.tsx` | 修改 |
| `src/components/ReviewPanel.tsx` | 修改（加模板） |
| `src/pages/DrugRecommendation.tsx` | 修改（移除 ReviewPanel） |
| `src/pages/HomePage.tsx` | 修改 |
| `src/pages/LoginPage.tsx` | 修改 |
| `src/pages/MyRecords.tsx` | 新建 |
| `src/pages/ReviewDashboard.tsx` | 新建 |
| `src/pages/DrugDatabase.tsx` | 新建 |
| `src/pages/RecommendationStats.tsx` | 新建 |
| `src/pages/PrivacyVisualization.tsx` | 删除 |
