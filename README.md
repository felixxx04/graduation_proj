# 差分隐私保护的AI驱动个性化医疗用药推荐系统

[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2.2-brightgreen)](https://spring.io/projects/spring-boot)
[![React](https://img.shields.io/badge/React-18.2.0-blue)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

基于深度学习与差分隐私保护的医疗用药智能推荐系统，在提供精准用药建议的同时保护患者隐私数据。

## 功能特性

### 核心功能

- **智能药物推荐** - 基于 DeepFM 深度学习模型，结合患者特征进行个性化用药推荐
- **差分隐私保护** - 支持 Laplace/Gaussian 噪声机制，保护敏感医疗数据
- **隐私预算管理** - 实时追踪与管理隐私预算消耗 (ε, δ)
- **RAG 检索增强** - 集成向量数据库，提供药物知识检索能力
- **多角色权限控制** - 支持 admin/doctor/researcher 三种角色

### 系统模块

| 模块 | 功能 |
|------|------|
| 用户管理 | JWT 认证、角色权限控制 |
| 患者管理 | 患者信息、健康档案 CRUD |
| 药物推荐 | DeepFM 模型推理、差分隐私噪声注入 |
| 隐私配置 | ε/δ 参数配置、预算追踪 |
| 可视化 | 隐私预算消耗、推荐结果可视化 |

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ 首页     │ │ 药物推荐 │ │ 隐私配置 │ │ 可视化面板   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend (Spring Boot)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ Auth API │ │ Drug API │ │Patient API│ │ Privacy API  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MySQL     │    │  Model Service  │    │   RAG Module    │
│  Database   │    │   (FastAPI)     │    │  (ChromaDB)     │
└─────────────┘    │   DeepFM + DP   │    └─────────────────┘
                   └─────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Framer Motion |
| **后端** | Spring Boot 3.2, MyBatis, Spring Security, JWT |
| **数据库** | MySQL 8.0 |
| **模型服务** | Python, FastAPI, PyTorch, NumPy, Pandas |
| **RAG 模块** | ChromaDB, Sentence Transformers |
| **隐私保护** | 差分隐私 (Laplace/Gaussian 机制) |

## 快速开始

### 环境要求

- **Node.js** >= 18.0
- **Java** >= 17
- **Python** >= 3.10
- **MySQL** >= 8.0
- **Maven** >= 3.8

### 1. 克隆项目

```bash
git clone https://github.com/felixxx04/graduation_proj.git
cd graduation_proj
```

### 2. 数据库配置

```bash
# 创建数据库并导入表结构
mysql -u root -p < medical-backend/sql/schema.sql

# 导入初始数据
mysql -u root -p < medical-backend/sql/init_data.sql
mysql -u root -p < medical-backend/sql/drug_data.sql
```

### 3. 后端启动

```bash
cd medical-backend

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入数据库密码和 JWT 密钥

# 启动服务
mvn spring-boot:run
```

后端服务运行在 `http://localhost:8080`

### 4. 模型服务启动

```bash
cd medical-model

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-rag.txt  # 可选：RAG 功能

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

模型服务运行在 `http://localhost:8001`

### 5. 前端启动

```bash
# 根目录
npm install
npm run dev
```

前端运行在 `http://localhost:5173`

## 项目结构

```
graduation_proj/
├── src/                          # 前端源码
│   ├── components/               # React 组件
│   ├── pages/                    # 页面组件
│   │   ├── HomePage.tsx
│   │   ├── DrugRecommendation.tsx
│   │   ├── PrivacyConfig.tsx
│   │   ├── PrivacyVisualization.tsx
│   │   ├── PatientRecords.tsx
│   │   └── AdminDashboard.tsx
│   ├── lib/                      # 工具函数
│   └── App.tsx                   # 路由配置
│
├── medical-backend/              # 后端源码
│   ├── src/main/java/com/medical/
│   │   ├── controller/           # REST 控制器
│   │   ├── service/              # 业务逻辑
│   │   ├── entity/               # 实体类
│   │   ├── repository/           # 数据访问层
│   │   ├── security/             # 安全配置
│   │   └── config/               # 配置类
│   ├── src/main/resources/
│   │   └── application.yml       # 配置文件
│   └── sql/                      # 数据库脚本
│       ├── schema.sql
│       ├── init_data.sql
│       └── drug_data.sql
│
├── medical-model/                # 模型服务源码
│   ├── app/
│   │   ├── models/               # DeepFM 模型
│   │   ├── services/             # 推理服务
│   │   ├── rag/                  # RAG 模块
│   │   └── main.py               # FastAPI 入口
│   ├── data/                     # 模型数据
│   └── saved_models/             # 训练好的模型
│
└── docs/                         # 文档
```

## API 文档

### 后端 API (Port 8080)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/me` | GET | 获取当前用户 |
| `/api/drugs` | GET | 获取药物列表 |
| `/api/patients` | GET/POST | 患者管理 |
| `/api/recommendation/predict` | POST | 获取用药推荐 |
| `/api/privacy/config` | GET/PUT | 隐私配置管理 |

### 模型服务 API (Port 8001)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/model/status` | GET | 模型状态 |
| `/model/predict` | POST | 推理请求 |
| `/model/train` | POST | 模型训练 |

## 隐私机制说明

### 差分隐私参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| ε (epsilon) | 隐私预算，越小隐私保护越强 | 0.1 |
| δ (delta) | 隐私泄露概率上限 | 1e-5 |
| 敏感度 | 查询函数的最大变化范围 | 1.0 |
| 噪声机制 | Laplace / Gaussian | Laplace |

### 隐私预算追踪

系统自动追踪每次推理消耗的隐私预算，当累计消耗超过预设阈值时发出警告。

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | 请查看部署文档 | admin |
| doctor1 | 请查看部署文档 | doctor |
| researcher1 | 请查看部署文档 | researcher |

> ⚠️ 生产环境请务必修改默认密码

## 许可证

本项目采用 [MIT](LICENSE) 许可证。
