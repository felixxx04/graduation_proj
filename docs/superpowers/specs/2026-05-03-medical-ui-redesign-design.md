# MediAI 医疗平台 UI/UX 视觉升级 — 设计文档

## 概述

将智医荐药前端从现有 "Clinical IA"（边框层次、无阴影、深青色）设计语言，全面升级为国际顶级医疗科技产品风格——深色主题 + 藏青主色 + 蓝绿强调 + 现代 SaaS 交互。

**状态**: 已确认  
**日期**: 2026-05-03  
**技术栈**: React 18 + TypeScript + Vite + Tailwind CSS

---

## 设计理念

### 核心定位
国际顶级医疗科技企业产品风格：专业、可信赖、科技感与人文关怀兼具。

### 参考方向
- 现代精准医疗 SaaS 平台
- AI 驱动的临床决策支持系统
- Dark-first 设计（深度专业感）

---

## 色彩系统

### 背景层次
```
Base:    #060f1e  — 页面底色
Surface: #0a1628  — 卡片、容器
Elevated:#0f2744  — 悬浮层、模态框
Overlay: #132f4c  — 最高层级
```

### 品牌色
```
Primary: #0ea5e9 (sky-500)    — 主按钮、链接、活动状态
Primary Dark: #0284c7 (sky-600) — 按钮渐变深色端
Accent:  #14b8a6 (teal-500)   — 强调色、安全状态、数据高亮
Accent Light: #5eead4 (teal-300) — 浅强调文字
```

### 语义色
```
Success:  #22c55e (green-500)   — 匹配状态、安全标记
Warning:  #f59e0b (amber-500)   — 需审核标记、警告
Danger:   #ef4444 (red-500)     — 禁忌、排除、错误
```

### 文字层级
```
Primary:   #f8fafc  — 标题、重要文字
Secondary: #cbd5e1  — 正文、描述
Tertiary:  #94a3b8  — 辅助信息
Disabled:  #64748b  — 禁用、占位符
```

---

## 字体系统

全部使用系统原生无衬线字体栈：

```css
font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont,
             'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
```

| 层级 | 大小 | 字重 | 用途 |
|------|------|------|------|
| Hero Title | 36-48px | 800 | 首页大标题 |
| Section Header | 22px | 700 | 区域标题 |
| Card Title | 16px | 600 | 卡片标题 |
| Body | 15px | 400 | 正文 |
| Caption | 13px | 400 | 辅助说明 |
| Micro | 11px | 600 | 标签、元数据 |

---

## 圆角 & 阴影 & 间距

### 圆角 (8px base unit)
```
4px  — 小徽章、标签
8px  — 输入框、小按钮
10px — 标准按钮、卡片
12px — 大卡片、模态框
16px — Hero 卡片、CTA 区域
24px — 胶囊按钮、pill
```

### 阴影深度
```
shadow-xs:  0 1px 3px rgba(0,0,0,0.3)   — 默认卡片
shadow-sm:  0 4px 12px rgba(0,0,0,0.4)  — hover 卡片
shadow-md:  0 8px 24px rgba(0,0,0,0.5)  — 模态框
shadow-lg:  0 16px 40px rgba(0,0,0,0.6) — 最高层
shadow-glow-primary: 0 0 20px rgba(14,165,233,0.15) — 按钮光晕
shadow-glow-teal: 0 0 20px rgba(20,184,166,0.12)    — 卡片边框光晕
```

### 间距 (8px base)
```
4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px
```

---

## 组件规范

### 按钮
- **形状**: 默认圆角 10px，胶囊变体 24px
- **颜色**: `linear-gradient(135deg, #0ea5e9, #0284c7)` 渐变
- **阴影**: 默认 `0 2px 8px rgba(14,165,233,0.3)`
- **hover**: `scale(1.02)` + 阴影加深（200ms ease-out）
- **active**: `scale(0.98)` + 阴影减弱
- **loading**: 使用品牌色 spinner
- **二次按钮**: 透明底 + `rgba(255,255,255,0.1)` 边框，hover 背景变亮
- **危险按钮**: 红色半透明底 + 红色边框

### 卡片
- **默认**: `#0f2744` 背景，`1px rgba(255,255,255,0.06)` 边框，`shadow-xs`
- **hover**: `translateY(-3px)` + `shadow-sm` + 边框色变为 `rgba(14,165,233,0.15)`（光晕效果），200ms ease-out
- **active**: 渐变背景 + primary 半透明边框
- **禁用**: opacity 0.5，pointer-events none

### 输入框
- **默认**: `#0a1628` 背景，`1px rgba(255,255,255,0.1)` 边框
- **focus**: 边框变 `#0ea5e9` + `box-shadow: 0 0 0 3px rgba(14,165,233,0.15)`（光晕效果）
- **error**: 边框变 `#ef4444`，placeholder 色变红
- **disabled**: opacity 0.4，cursor not-allowed

### 导航栏
- **默认**: `rgba(10, 22, 40, 0.85)` + `backdrop-filter: blur(16px)`（毛玻璃）
- **滚动后**: `rgba(10, 22, 40, 0.95)` + 边框加深
- **活动项**: primary 色 pill 背景 + primary 文字
- **非活动项**: tertiary 色文字，hover 变 secondary
- **移动端**: 全屏抽屉菜单，与桌面端一致的玻璃态

### 标签/徽章
- 半透明背景 + 彩色边框 + 大写字母间距
- 变体: primary, accent, success, warning, danger
- 形状: 小圆角，可带彩色圆点指示器

### 表格
- **表头**: `#0a1628` 背景，底部双倍高度边框，大写字母间距
- **行**: 交替背景色（无底色 / `rgba(14,165,233,0.04)`）
- **hover**: 整行 primary 色微亮
- **操作**: primary 色链接文字

### 骨架屏
- 使用 primary 色 + accent 色脉冲动画（替代灰色）
- `background: linear-gradient(90deg, rgba(14,165,233,0.08), rgba(20,184,166,0.06), rgba(14,165,233,0.08))`
- 动画: 1.5s 无限循环

---

## 页面布局

### 首页（HomePage）
1. **Hero 区域** — 非对称左右分割：
   - 左侧：标签 + 标题（含渐变色文字）+ 描述 + CTA 按钮
   - 右侧：隐私预算 ε 视觉图形 + 几何圆形装饰
   - 背景：深蓝渐变（#060f1e → #0f2744）
   - 装饰元素：半透明同心圆 + 散落光点
2. **统计数据行** — 4列网格：ε≤1.0 / 92%+ / 5000+ / 10000+
3. **核心功能** — 2×2 网格：差分隐私 / 深度学习 / 个性化 / 安全可控
4. **CTA 区域** — 渐变背景 + 大圆角 + 双按钮

### 用药推荐页（DrugRecommendation）
- 双输入模式切换（pill 标签切换）
- 深色表单网格布局
- 药物结果卡片（4列网格）
- 排名颜色编码（1绿 2青 3蓝 4琥珀）
- 排除药物列表（可折叠，红色标记）
- 隐私预算展示

### 患者档案页（PatientRecords）
- 搜索栏 + 新增按钮
- 深色斑马纹表格
- hover 行高亮
- 分页器（深色主题样式）
- 模态框编辑表单

### 其他页面
- 隐私配置页、可视化页、管理后台、登录页 — 统一应用深色主题

---

## 动画与过渡

### 页面切换
- 路由切换使用 `framer-motion` 的 `AnimatePresence`
- fade + slide-up（200-300ms ease-out）

### 微交互
- 按钮：hover scale(1.02) + shadow↑ (200ms)
- 卡片：hover translateY(-3px) + border glow (200ms)
- 输入框：focus border + ring glow (150ms)
- 导航：滚动渐变背景（300ms）

### 数据展示
- 药片卡片：staggered entrance（每个延迟 50ms）
- 统计数字：count-up 动画

### 无障碍
- `prefers-reduced-motion` 尊重用户系统设置
- 所有动画时长缩短为 0.01ms

---

## 实施范围

### 改动文件

| 文件 | 改动 |
|------|------|
| `src/index.css` | 完全重写 — 新色彩变量、新组件类、新动画 |
| `tailwind.config.ts` | 更新色彩、圆角、阴影、动画配置 |
| `src/components/ui/button.tsx` | 渐变 + 阴影 + scale 动画变体 |
| `src/components/ui/card.tsx` | 微阴影 + hover lift + 光晕边框 |
| `src/components/ui/input.tsx` | 深色底 + focus glow |
| `src/components/Layout.tsx` | 毛玻璃导航 + 滚动效果 |
| `src/pages/HomePage.tsx` | 非对称 Hero + 几何装饰 + 新卡片样式 |
| `src/pages/DrugRecommendation.tsx` | 深色表单 + 药物卡片排名色 |
| `src/pages/PatientRecords.tsx` | 深色表格 + 斑马纹 |
| `src/pages/*.tsx` | 所有页面应用统一深色主题 |

### 不改动
- 后端 API、模型服务、数据库
- 业务逻辑、状态管理、路由结构
- 功能行为、数据处理

---

## 验证标准

1. 所有页面在深色主题下可读性良好（WCAG AA 对比度 ≥ 4.5:1）
2. 按钮 hover/active 动画流畅（60fps）
3. 卡片 hover 效果正常（上移 + 光晕）
4. 导航滚动毛玻璃效果正常
5. 输入框 focus 光晕效果正常
6. 表格斑马纹 + hover 高亮正常
7. 移动端响应式布局正常
8. 打印样式正确处理深色背景
9. 系统 `prefers-reduced-motion` 正常降级
10. TypeScript 编译零错误
