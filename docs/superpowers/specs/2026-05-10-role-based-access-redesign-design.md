# 基于角色的访问控制重设计 — 设计文档

> 日期：2026-05-10
> 状态：已确认

## 目标

将医疗用药推荐系统从当前 admin/doctor/researcher 三角色重构为 admin/doctor/patient 三角色，明确患者发起推荐→医生审核→管理员监控的分层职责，并新增药物数据库浏览、推荐统计分析等管理端功能。

## 一、角色体系

### 1.1 三角色定义

| 角色 | 数据库值 | 核心职责 | 禁止访问 |
|------|---------|---------|----------|
| patient | `patient` | 输入症状获取用药推荐，查看审核结果和历史记录 | 患者档案、推荐审核、后台管理 |
| doctor | `doctor` | 管理患者档案，审核用药推荐，出具诊疗建议 | 隐私配置、后台管理 |
| admin | `admin` | 所有功能 + 药物数据库 + 推荐统计 + 隐私配置 + 用户管理 | — |

### 1.2 角色变更对照

| 变更 | 说明 |
|------|------|
| `researcher` → 删除 | 无人实际使用，数据库枚举、测试账号、前端类型全部移除 |
| 原 `doctor1` → `patient1` | 角色从 doctor 改为 patient |
| 新增 `doctor1` | 新建真正的医生账号 |

### 1.3 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | admin |
| doctor1 | admin123 | doctor |
| patient1 | admin123 | patient |

---

## 二、导航与路由

### 2.1 导航矩阵

| 页面 | 路径 | Patient | Doctor | Admin |
|------|------|:---:|:---:|:---:|
| 首页 | `/` | ✓ | ✓ | ✓ |
| 用药推荐 | `/recommendation` | ✓ | — | — |
| 我的记录 | `/my-records` | ✓ | — | — |
| 患者档案 | `/patients` | — | ✓ | ✓ |
| 推荐审核 | `/review` | — | ✓ | — |
| 药物数据库 | `/drug-database` | — | — | ✓ |
| 推荐统计 | `/recommendation-stats` | — | — | ✓ |
| 隐私配置 | `/privacy` | — | — | ✓ |
| 后台管理 | `/admin` | — | — | ✓ |

### 2.2 各页面说明

**用药推荐 `/recommendation`（Patient only）**
- 患者输入症状/疾病名，系统生成推荐
- 显示推荐结果含安全级别标签、路由路径、证据等级
- **只读展示**，审核操作已移至医生端
- 显示审核状态标签（待审核/已确认/已修改/已拒绝）

**我的记录 `/my-records`（Patient only，新增）**
- 患者查看自己的推荐历史列表
- 每条记录显示：日期、输入症状、推荐药物、审核状态、医生诊疗建议

**推荐审核 `/review`（Doctor only，新增）**
- 待审核推荐列表（按患者分组）
- 点击进入审核面板：患者信息 + 原始症状 + 系统推荐（候选药+路由路径+安全级别）
- 审核操作：确认/修改/拒绝
- 诊疗建议：模板选择 + 自由文本
- 历史审核记录查看

**药物数据库 `/drug-database`（Admin only，新增）**
- 展示系统内 1,815 种药物的完整临床数据
- 包含：药物名称（中英文）、适应症、禁忌症、ATC 分类、副作用、交互关系、妊娠分级
- 搜索和筛选功能
- **只读展示**，不提供编辑功能

**推荐统计 `/recommendation-stats`（Admin only，新增）**
- 推荐分布统计图表（哪些药推荐最多、各疾病类别推荐量、审核通过率）
- 实时推荐演示（输入任意疾病查看完整路由过程）
- 整合原 `/visualization` 页面的隐私预算可视化

### 2.3 移除的页面

| 页面 | 原因 |
|------|------|
| `/visualization` | 内容整合到 `/recommendation-stats` |
| Researcher 相关逻辑 | 角色已删除 |

---

## 三、数据库改动

### 3.1 sys_user 表 — 角色枚举

```sql
-- 迁移 SQL
ALTER TABLE sys_user 
MODIFY COLUMN role ENUM('admin', 'doctor', 'patient') DEFAULT 'patient';

-- 更新现有数据
UPDATE sys_user SET role = 'patient' WHERE username = 'doctor1';
-- 删除 researcher 账号（如存在）
DELETE FROM sys_user WHERE username = 'researcher1';
-- 新增医生账号由 init_data.sql 处理
```

### 3.2 recommendation 表 — 新增审核状态

```sql
ALTER TABLE recommendation 
ADD COLUMN review_status ENUM('pending', 'confirmed', 'modified', 'rejected') 
DEFAULT 'pending' COMMENT '审核状态' AFTER result_data;
```

### 3.3 review_log 表 — 新增诊疗建议字段

```sql
ALTER TABLE review_log
ADD COLUMN treatment_advice TEXT COMMENT '医生诊疗建议（自由文本）' AFTER doctor_reason,
ADD COLUMN treatment_template VARCHAR(50) COMMENT '使用的诊疗模板名称' AFTER treatment_advice;
```

### 3.4 init_data.sql — 测试账号更新

删除 researcher1 账号行，将原 doctor1 改为 patient1，新增 doctor1 账号行。

### 3.5 数据库迁移文件

创建 `medical-backend/sql/migration_v2_roles.sql`，包含上述所有 ALTER/UPDATE 语句，按顺序执行。

---

## 四、后端 API 改动

### 4.1 SecurityConfig 角色权限重配

```java
// 修改后
.antMatchers("/api/admin/**").hasRole("ADMIN")
.antMatchers("/api/patients/**").hasAnyRole("ADMIN", "DOCTOR")
.antMatchers("/api/recommendations/**").authenticated()  // 所有角色可访问
.antMatchers("/api/review/**").hasAnyRole("DOCTOR", "ADMIN")  // 加角色限制
.antMatchers("/api/privacy/**").hasRole("ADMIN")  // 缩小为 admin only
.antMatchers("/api/drugs/**").hasAnyRole("ADMIN", "DOCTOR")
.antMatchers("/api/dashboard/**").hasAnyRole("ADMIN", "DOCTOR")
```

主要变化：
- `/api/privacy/**` 从 `ADMIN,DOCTOR,RESEARCHER` 缩小为 `ADMIN`
- `/api/review/**` 从 `authenticated()` 改为 `DOCTOR, ADMIN`
- `/api/drugs/**` 保持 `ADMIN, DOCTOR`（药物数据供推荐审核参考）
- 删除所有 researcher 引用

### 4.2 新增 API

| 方法 | 路径 | 用途 | 角色 |
|------|------|------|------|
| GET | `/api/recommendations/my-history` | 患者查看自己的推荐历史 | patient |
| GET | `/api/review/pending` | 医生获取待审核推荐列表 | doctor, admin |
| GET | `/api/drugs/database` | 管理员获取药物完整数据列表 | admin |
| GET | `/api/stats/recommendations` | 推荐统计数据 | admin |

### 4.3 现有 API 修改

| API | 修改内容 |
|-----|---------|
| `POST /api/auth/login` | 登录提示文本更新（去掉 researcher 提示） |
| `GET /api/auth/me` | 返回的角色对应新枚举 |
| `POST /api/recommendations/generate` | 新推荐自动设 review_status='pending' |
| `POST /api/review/log` | 保存诊疗建议字段（treatment_advice, treatment_template），同步更新 recommendation.review_status |

### 4.4 JwtFilter

角色映射逻辑不变（`ROLE_` + role.toUpperCase()），新角色 `patient` 自动变为 `ROLE_PATIENT`。

---

## 五、前端改动

### 5.1 类型系统

```typescript
// src/lib/authStore.tsx
export type UserRole = 'admin' | 'doctor' | 'patient'

// 删除 normalizeUser 中的 researcher 映射
// 删除 'user' 类型，所有引用替换为 'patient'
```

### 5.2 权限矩阵（permissions.ts）

```typescript
export const ROLE_FEATURES: Record<UserRole, AppFeature[]> = {
  patient: ['recommendation', 'my_records'],
  doctor:  ['patients', 'review'],
  admin:   ['patients', 'review', 'drug_database', 'recommendation_stats', 'privacy', 'admin'],
}
```

### 5.3 路由重构（App.tsx）

```tsx
// 公共路由
<Route path="/login" element={<LoginPage />} />
<Route path="/" element={<Layout />}>
  <Route index element={<HomePage />} />

  // Patient（需认证）
  <Route element={<RequireAuthModal />}>
    <Route path="recommendation/*" element={<DrugRecommendation />} />
    <Route path="my-records/*" element={<MyRecords />} />
  </Route>

  // Doctor + Admin
  <Route element={<RequireRole role="doctor" />}>
    <Route path="patients/*" element={<PatientRecords />} />
    <Route path="review/*" element={<ReviewDashboard />} />
  </Route>

  // Admin only
  <Route element={<RequireRole role="admin" />}>
    <Route path="drug-database/*" element={<DrugDatabase />} />
    <Route path="recommendation-stats/*" element={<RecommendationStats />} />
    <Route path="privacy/*" element={<PrivacyConfig />} />
    <Route path="admin/*" element={<AdminDashboard />} />
  </Route>
</Route>
```

### 5.4 导航栏（Layout.tsx）

按 ROLE_FEATURES 动态渲染，角色显示标签：
- admin → "管理员"
- doctor → "医生"
- patient → "患者"

登录弹窗提示更新测试账号（patient1 / doctor1 / admin）。

### 5.5 DrugRecommendation.tsx（患者端）

- 移除 `<ReviewPanel />` 组件引用
- 推荐结果卡片下方显示审核状态标签：
  - 待审核（灰色）、已确认（绿色）、已修改（蓝色）、已拒绝（红色）
- 若已有审核结果，展示医生诊疗建议（只读）

### 5.6 新增页面

**MyRecords.tsx（患者"我的记录"）**
- 调用 `GET /api/recommendations/my-history`
- 列表展示：日期、输入症状、推荐药物、审核状态
- 展开查看医生诊疗建议

**ReviewDashboard.tsx（医生"推荐审核"）**
- 调用 `GET /api/review/pending` 展示待审核列表
- 点击展开审核详情 + ReviewPanel 组件
- 审核提交后刷新列表

**DrugDatabase.tsx（管理员"药物数据库"）**
- 调用 `GET /api/drugs/database`
- 表格展示 + 搜索 + 筛选（适应症、ATC分类、身体系统）
- 展开行查看完整临床数据

**RecommendationStats.tsx（管理员"推荐统计"）**
- 推荐分布图表（柱状图/饼图）
- 实时推荐演示（输入疾病→展示完整路由路径）
- 整合隐私预算消耗可视化

### 5.7 移除的文件

| 文件 | 原因 |
|------|------|
| `src/pages/PrivacyVisualization.tsx` | 整合入 RecommendationStats.tsx |
| 所有 researcher 引用 | 角色已删除 |

---

## 六、医生审核流程

```
┌──────────┐    ┌──────────────┐    ┌─────────────────┐
│ Patient   │    │  System      │    │  Doctor         │
│ 输入症状   │───▶│  知识路由     │    │                 │
│           │    │  安全过滤     │    │                 │
│           │    │  DeepFM排序   │    │                 │
└──────────┘    └──────┬───────┘    └─────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ recommendation │
              │ review_status  │
              │ = 'pending'    │
              └───────┬────────┘
                      │
                      ▼
              ┌─────────────────────────┐
              │ Doctor /review          │
              │                         │
              │ 看到待审核列表            │
              │ 点击某条记录              │
              │ ┌─────────────────────┐ │
              │ │ 患者信息 + 原始症状   │ │
              │ │ 系统推荐（路由路径）  │ │
              │ │                     │ │
              │ │ ✅ 确认推荐          │ │
              │ │   → 选模板(可选)     │ │
              │ │   → 写诊疗建议       │ │
              │ │                     │ │
              │ │ ✏️ 修改选择          │ │
              │ │   → 另选药物         │ │
              │ │   → 选模板(可选)     │ │
              │ │   → 写诊疗建议       │ │
              │ │                     │ │
              │ │ ❌ 拒绝推荐          │ │
              │ │   → 填写拒绝理由     │ │
              │ └─────────────────────┘ │
              └──────────┬──────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ review_log 写入     │
              │ recommendation      │
              │ .review_status 更新 │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Patient /my-records │
              │ 可查看审核结果+建议   │
              └─────────────────────┘
```

### 诊疗建议模板（前端硬编码）

| 模板名 | 内容 |
|--------|------|
| 标准用法 | 建议使用[药物名]，每日[N]次，每次[剂量]，连用[N]天。 |
| 递增剂量 | 起始剂量[小剂量]，根据耐受情况逐步调整至[目标剂量]。 |
| 联合用药 | 建议[药物A]联合[药物B]，注意监测[相互作用/不良反应]。 |
| 对症治疗 | 针对[症状]进行对症治疗，如症状持续或加重请及时复诊。 |
| 自定义 | 医生自行输入完整建议 |

---

## 七、文件改动清单

### 数据库
| 文件 | 操作 |
|------|------|
| `medical-backend/sql/schema.sql` | 修改 role ENUM，recommendation 表加 review_status，review_log 加字段 |
| `medical-backend/sql/init_data.sql` | 更新测试账号 |
| `medical-backend/sql/migration_v2_roles.sql` | **新建** 迁移脚本 |

### 后端
| 文件 | 操作 |
|------|------|
| `medical-backend/.../config/SecurityConfig.java` | 修改角色路径权限 |
| `medical-backend/.../controller/AuthController.java` | 登录提示更新 |
| `medical-backend/.../controller/RecommendationController.java` | 新增 my-history 端点，generate 加 pending 状态 |
| `medical-backend/.../controller/ReviewController.java` | 新增 pending 端点，保存诊疗建议 |
| `medical-backend/.../controller/DrugController.java` | 新增 database 端点 |
| `medical-backend/.../controller/StatsController.java` | **新建** 推荐统计端点 |

### 前端
| 文件 | 操作 |
|------|------|
| `src/lib/authStore.tsx` | UserRole 类型改为 admin/doctor/patient |
| `src/lib/permissions.ts` | 重写 ROLE_FEATURES |
| `src/App.tsx` | 路由重构 |
| `src/components/Layout.tsx` | 导航按角色重建，登录提示更新 |
| `src/components/AuthGuards.tsx` | RequireRole 适配新角色 |
| `src/pages/LoginPage.tsx` | 提示文本更新 |
| `src/pages/HomePage.tsx` | CTA 按钮按新角色调整 |
| `src/pages/DrugRecommendation.tsx` | 移除 ReviewPanel，改为只读审核状态展示 |
| `src/pages/MyRecords.tsx` | **新建** 患者推荐历史 |
| `src/pages/ReviewDashboard.tsx` | **新建** 医生审核页 |
| `src/pages/DrugDatabase.tsx` | **新建** 管理员药物数据库 |
| `src/pages/RecommendationStats.tsx` | **新建** 管理员推荐统计 |
| `src/components/ReviewPanel.tsx` | 从患者端移至医生端复用，加诊疗建议模板 |
| `src/pages/PrivacyVisualization.tsx` | **删除** |
