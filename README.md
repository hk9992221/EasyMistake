# EasyMistake

EasyMistake 是一个面向错题管理与试题整理的全栈项目，支持试题录入、AI 图片识别辅助、组卷导出、复习追踪与基础管理能力。

项目采用前后端分离架构：
- `frontend`：Next.js 14 + TypeScript
- `backend`：FastAPI + SQLAlchemy + Alembic + PostgreSQL

## 功能概览

- 用户认证与权限管理（普通用户 / 管理员）
- 试题管理（题干、选项、答案、标签、知识点）
- 图片上传与对象存储（S3 兼容）
- AI 识别辅助录入（OCR + 结构化提取）
- 组卷与导出（Markdown / LaTeX ZIP）
- 今日复习、错因统计、基础数据看板
- 管理端（用户、题目、组卷、API 日志）

## 技术栈

### Frontend
- Next.js 14（App Router）
- React 18 + TypeScript
- Tailwind CSS + Radix UI + shadcn/ui
- TanStack Query + Zustand

### Backend
- FastAPI
- SQLAlchemy（Async）+ Alembic
- PostgreSQL（`asyncpg`）
- OpenAI 兼容接口（默认 DashScope 兼容地址）
- S3 兼容对象存储（`boto3`）

## 项目结构

```text
EasyMistake/
├─ frontend/                # Next.js 前端
│  ├─ src/app/              # 页面与路由
│  ├─ src/components/       # UI 组件
│  ├─ src/lib/api/          # API 客户端封装
│  └─ .env.example
└─ backend/                 # FastAPI 后端
   ├─ api/
   │  ├─ api/v1/            # 业务接口
   │  ├─ core/              # 配置、鉴权、数据库
   │  ├─ models/            # 数据模型
   │  └─ services/          # 业务服务
   ├─ alembic/              # 迁移脚本
   ├─ alembic.ini           # Alembic 配置
   ├─ requirements.txt      # 后端依赖
   ├─ exports/              # 导出产物目录（运行期）
   └─ .env.example
```

## 快速开始

### 1. 环境要求

- Node.js 18+
- Python 3.10+（建议 3.11）
- PostgreSQL 14+

### 2. 启动后端

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

接口文档：
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. 启动前端

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

访问：`http://localhost:3000`

## 环境变量说明

### Backend 关键变量（`backend/.env`）
- `DATABASE_URL` / `DATABASE_URL_SYNC`：数据库连接
- `SECRET_KEY`：JWT 密钥
- `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET`
- `OPENAI_API_KEY` / `OPENAI_BASE_URL`
- `FRONTEND_BASE_URL`（默认 `http://localhost:3000`）

### Frontend 关键变量（`frontend/.env.local`）
- `NEXT_PUBLIC_API_URL`：后端地址（如 `http://localhost:8000`）
- `INTERNAL_API_ORIGIN`：Next 服务端代理目标
- `NEXTAUTH_URL` / `NEXTAUTH_SECRET`

## 开发说明

- 后端 API 前缀：`/api/v1`
- 后端包含嵌入式导出 Worker（可通过环境变量关闭自动启动）
- 注册流程支持邀请码校验（管理员可创建邀请码）

## 贡献指南

1. Fork 仓库并新建分支
2. 提交清晰的 Commit 信息
3. 提交 PR 并说明变更动机与影响范围

## License

MIT
