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
- 复习队列按学科筛选与分页，批量展示题干、图片、答案及解析
- 一键生成当前学科的全部待复习题目组卷，按账号、日期与学科复用
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

更新依赖后，先在 `backend` 目录执行 `alembic upgrade head`，再启动服务。迁移包含批改记录表、查询索引和完整录题的防重复提交字段，不自动归属旧 JSON 数据。

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

`GET /api/v1/reviews/today` 和 `/reviews/queue` 支持 `page`、`page_size`（1–100）、`subject` 和 `include_details`，返回真实总数及分页信息。开启详情后批量获取当前页的题干、题干图片、答案和解析，不再逐题请求；今日范围按 `APP_TIMEZONE` 计算。

`POST /api/v1/reviews/daily-paper-set` 接收 `{}` 或 `{"subject":"数学"}`，在一个事务内按当前到期队列生成或更新组卷，包含全部匹配题目，不受当前分页影响。同账号、同一天、同学科的重复请求复用已有自动组卷；保留仍在卷中的题目分值与分组，不覆盖仅仅同名的手动组卷。生成成功后可继续创建 LaTeX 导出任务；导出未完成时可到组卷的导出历史下载。

录题页面先上传图片，再调用 `POST /api/v1/questions/with-answer`，将题目、题干图片关联和答案放在同一事务中保存。请求格式为 `{ "request_id": "UUID", "question": { ... }, "answer": { ... } }`，无答案时可省略 `answer`。同账号使用相同请求编号重试相同内容，会返回已保存的题目；内容不同或该题已删除则返回 409。页面内重试会复用已上传图片及请求编号，避免网络错误造成重复录题；图片上传本身独立于保存事务。

`POST /api/v1/paper-sets/{id}/items/batch` 每批接收 1–1000 道不重复的题目，先校验全部题目权限、删除状态、顺序与分数，再一次提交。任意一项失败，整批保持原状。

图片文件接口 `/api/v1/images/{id}/file` 只接受 `Authorization: Bearer ...` 请求头，不再接受 URL 中的登录令牌。前端按图片 ID 获取 Blob 并展示，复用内存中的图片请求；服务端返回 `private, no-store` 缓存策略。此次升级需同时更新前后端，并完成数据库迁移；自行调用图片接口的客户端也需改用请求头。

图片上传会检查真实格式、完整性和像素，支持 PNG、JPEG、WebP 和静态 GIF。默认上限为 20 MiB、4000 万像素，可用 `IMAGE_MAX_UPLOAD_BYTES`、`IMAGE_MAX_PIXELS` 调整。直传接口仍为 `/images/upload`；自行使用 `/images/upload-url` 时须提供 `filename`、`content_type`、`size_bytes`，签名会绑定文件长度。登记接口 `/images` 只接受当前账号的 `uploads/` 临时对象，服务器验证实际字节后复制到独立图片路径，忽略客户端自报的元数据。

被题目、答案或识别记录引用的图片不能删除。未被引用的图片会先在同一事务中删除数据库记录并创建 `IMAGE_CLEANUP` 任务，再由 Worker 清理文件；存储故障会退避重试，Worker 中断也可恢复。部署时须更新并运行 Worker，关闭自动启动时应启动上文的独立 Worker。对象存储可为 `uploads/` 临时前缀设置过期清理规则，清理上传后未登记的文件。

录题草稿按账号保存在当前浏览器中，包含文字、所选图片、已上传图片编号和提交编号；刷新后自动恢复，成功录入后清除。草稿不跨设备同步，清理浏览器站点数据会删除草稿。退出或切换账号时页面缓存会重建，之前账号的请求结果不能覆盖新账号。

删除题目后可在“回收站”恢复，或点击删除提示中的“撤销”。`GET /questions/trash` 支持分页；`POST /questions/{id}/restore` 可重复调用，保留原有图片、答案与复习进度。普通账号只能查看和恢复自己的题目，管理员可以管理全部题目。此次更新无新增数据库迁移，但需要安装更新后的后端依赖并同步发布前后端和 Worker。

## 验证

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
```

本地默认使用隔离的 SQLite 数据库；设置 `TEST_DATABASE_URL=postgresql+asyncpg://...` 可使用 PostgreSQL，每个测试创建临时 schema。CI 使用 PostgreSQL 16，执行全量迁移、迁移回滚再升级和同一组测试。OCR 和 S3 在测试中使用替身，不调用付费服务。

前端验证：`cd frontend && npm ci && npm run type-check && npm run build`。

浏览器回归：在前端构建后执行 `npx playwright install --with-deps chromium && npm run test:e2e`，覆盖草稿刷新与提交重试、账号缓存隔离、答案图片类型和回收站恢复。测试使用模拟 API，不访问真实账号或对象存储。

后端运行依赖锁定在 `requirements.lock.txt`，更新方式：`uv pip compile requirements.txt --universal --python-version 3.11 --no-annotate -o requirements.lock.txt`。

## 贡献指南

1. Fork 仓库并新建分支
2. 提交清晰的 Commit 信息
3. 提交 PR 并说明变更动机与影响范围

## License

MIT
