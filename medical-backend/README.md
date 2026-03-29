# 医疗推荐系统后端

差分隐私保护的 AI 驱动个性化医疗用药推荐系统 - 后端服务

## 项目结构

```
medical-backend/
├── sql/                    # 数据库脚本
│   ├── schema.sql          # 表结构
│   ├── init_data.sql       # 初始数据
│   └── drug_data.sql       # 药物数据
├── scripts/                # 工具脚本
│   ├── generate_patients.py    # 模拟患者数据生成
│   └── requirements.txt        # Python 依赖
└── README.md
```

## 环境要求

- MySQL 8.0+
- Python 3.10+ (仅用于数据生成脚本)

## 快速开始

### 1. 创建数据库

```bash
mysql -u root -p < sql/schema.sql
```

### 2. 插入初始数据

```bash
mysql -u root -p < sql/init_data.sql
mysql -u root -p < sql/drug_data.sql
```

### 3. 生成模拟患者数据（可选）

```bash
pip install -r scripts/requirements.txt
python scripts/generate_patients.py -n 50 -p YOUR_PASSWORD
```

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| doctor1 | admin123 | 医生 |
| researcher1 | admin123 | 研究员 |

## 数据库表

- `sys_user` - 系统用户
- `patient` - 患者信息
- `patient_health_record` - 患者健康档案
- `drug` - 药物信息
- `recommendation` - 推荐记录
- `privacy_ledger` - 隐私预算账本
- `privacy_config` - 隐私配置
- `system_config` - 系统配置
- `operation_log` - 操作日志

## 后续开发

- SpringBoot 后端服务（进行中）
- Python 模型服务（待开发）
