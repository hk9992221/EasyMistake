# EasyMistake

EasyMistake 是一个面向错题管理与试题整理的全栈项目，支持试题录入、AI 图片识别辅助、组卷导出、复习追踪与基础管理能力。

项目采用前后端分离架构：
- `frontend`：Next.js 15 + TypeScript
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
- Next.js 15（App Router）
- React 19 + TypeScript
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

- Node.js 20+
- Python 3.11+（CI 使用 3.12）
- PostgreSQL 14+

### 2. 启动后端

```bash
cd backend
cp .env.example .env
pip install -r requirements.lock.txt
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
npm ci
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

## 开发说明

- 后端 API 前缀：`/api/v1`
- 后端内置 Worker，同时处理图片识别和导出任务（可通过环境变量关闭自动启动）
- 注册流程支持邀请码校验（管理员可创建邀请码）

## 升级与任务运行

更新依赖后，先在 `backend` 目录执行 `alembic upgrade head`，再启动服务。本次迁移增加批改记录表及查询索引，不自动归属旧 JSON 数据。

识别任务创建后直接入队，前端轮询状态；关闭窗口后，可从“识别记录”查看结果。`/extractions/{id}/retry` 只入队，重复点击会复用活动任务，已完成的任务不会再次识别。

`EXPORT_WORKER_AUTO_START` 和轮询配置兼容原变量名，目前同时控制识别和导出。若需要独立进程，将自动启动设为 `false` 后运行：

```bash
cd backend
python -m api.worker --worker-id worker-1
```

Worker 定期更新任务心跳。超过 `JOB_LEASE_TIMEOUT_SECONDS` 未更新的运行任务会标记失败，可显式重试；不会自动重复可能已经计费的 OCR 请求。OCR 单次请求超时由 `OCR_REQUEST_TIMEOUT_SECONDS` 控制。

简易批改接口现要求登录，只返回当前账号的记录。旧 `backend/data/simple_grading_records.json` 缺少账号归属，需指定已有账号导入（原文件保留，重复执行会跳过已导入记录）：

```bash
cd backend
python -m api.scripts.import_grading --file data/simple_grading_records.json --user-email your-account@example.com
```

历史作答的熟练度如有偏差，登录后调用 `POST /api/v1/reviews/recalculate`，将按作答顺序重算当前用户的进度，保留自我评价。

## 验证

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
```

本地默认使用隔离的 SQLite 数据库；设置 `TEST_DATABASE_URL=postgresql+asyncpg://...` 可使用 PostgreSQL，每个测试创建临时 schema。CI 使用 PostgreSQL 16，执行全量迁移、迁移回滚再升级和同一组测试。OCR 和 S3 在测试中使用替身，不调用付费服务。

前端验证：`cd frontend && npm ci && npm run type-check && npm run build`。

后端运行依赖锁定在 `requirements.lock.txt`，更新方式：`uv pip compile requirements.txt --universal --python-version 3.11 --no-annotate -o requirements.lock.txt`。

## 贡献指南

1. Fork 仓库并新建分支
2. 提交清晰的 Commit 信息
3. 提交 PR 并说明变更动机与影响范围

## License

MIT
