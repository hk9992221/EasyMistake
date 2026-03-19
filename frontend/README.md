# 题库管理系统前端

这是一个基于 Next.js 14 的题库管理系统前端项目。

## 技术栈

- **框架**: Next.js 14 (App Router)
- **语言**: TypeScript
- **样式**: Tailwind CSS
- **组件库**: shadcn/ui
- **状态管理**: Zustand
- **数据请求**: TanStack Query (React Query)
- **表单管理**: React Hook Form + Zod
- **HTTP 客户端**: Axios

## 项目结构

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router 页面
│   │   ├── dashboard/          # 主应用页面（需要认证）
│   │   ├── login/              # 登录页
│   │   ├── register/           # 注册页
│   │   ├── layout.tsx          # 根布局
│   │   ├── page.tsx            # 首页（重定向）
│   │   └── globals.css         # 全局样式
│   ├── components/
│   │   ├── ui/                 # shadcn/ui 基础组件
│   │   ├── layout/             # 布局组件（Sidebar, Header）
│   │   └── providers/          # Context Providers
│   ├── lib/
│   │   ├── api/                # API 客户端层
│   │   │   ├── client.ts       # Axios 客户端配置
│   │   │   ├── auth.ts         # 认证 API
│   │   │   ├── questions.ts    # 题目 API
│   │   │   ├── answers.ts      # 答案 API
│   │   │   ├── images.ts       # 图片 API
│   │   │   ├── papers.ts       # 整卷 API
│   │   │   ├── extractions.ts  # 识别任务 API
│   │   │   ├── paper-sets.ts   # 组卷 API
│   │   │   ├── exports.ts      # 导出 API
│   │   │   ├── submissions.ts  # 归档容器 API
│   │   │   ├── attempts.ts     # 做题记录 API
│   │   │   └── admin.ts        # 管理员 API
│   │   ├── hooks/              # 自定义 Hooks
│   │   │   └── use-auth.ts     # 认证 Hook
│   │   ├── store/              # Zustand 状态管理
│   │   │   └── auth.ts         # 认证状态
│   │   ├── validations/        # Zod 验证模式（待添加）
│   │   ├── utils.ts            # 工具函数
│   │   └── constants.ts        # 常量定义
│   └── types/
│       ├── models.ts           # 数据模型类型
│       ├── forms.ts            # 表单类型
│       └── index.ts            # 类型统一导出
├── .env.local                  # 环境变量
├── .env.example                # 环境变量示例
├── package.json                # 依赖配置
├── tsconfig.json               # TypeScript 配置
├── tailwind.config.ts          # Tailwind 配置
└── next.config.js              # Next.js 配置
```

## 已完成功能

### 1. 项目基础配置
- ✅ Next.js 14 项目初始化
- ✅ TypeScript 配置
- ✅ Tailwind CSS 配置
- ✅ shadcn/ui 组件库配置
- ✅ 环境变量配置

### 2. 类型系统
- ✅ 完整的数据模型类型定义（18 张表）
- ✅ 表单验证 schema（Zod）
- ✅ API 响应类型
- ✅ 分页和筛选参数类型

### 3. API 层
- ✅ Axios 客户端封装（拦截器、错误处理）
- ✅ 认证 API（登录、注册、获取当前用户）
- ✅ 题目 CRUD API
- ✅ 答案 CRUD API
- ✅ 图片上传和管理 API
- ✅ 整卷/资料源 API
- ✅ 识别任务 API
- ✅ 组卷 API
- ✅ 导出 API
- ✅ 归档容器 API
- ✅ 做题记录 API
- ✅ 管理员 API（用户、邀请码、日志）

### 4. 状态管理
- ✅ Zustand 认证状态管理
- ✅ 认证 Hook（useAuth）
- ✅ JWT token 持久化

### 5. 基础组件
- ✅ Button
- ✅ Input
- ✅ Card
- ✅ Label
- ✅ Query Provider（TanStack Query）
- ✅ Theme Provider（next-themes）

### 6. 布局和导航
- ✅ 侧边栏导航（包含所有功能模块）
- ✅ 头部组件
- ✅ 仪表盘布局
- ✅ 管理员功能区分显示

### 7. 认证页面
- ✅ 登录页面
- ✅ 注册页面
- ✅ 路由保护（仪表盘需要登录）

### 8. 仪表盘
- ✅ 欢迎页面
- ✅ 统计数据卡片
- ✅ 快速操作入口

## 待完成功能

### 高优先级
1. **题库管理模块**
   - 题目列表页（表格、筛选、搜索）
   - 题目详情页
   - 题目编辑页（支持 Markdown/LaTeX）
   - 新建题目页

2. **识别任务模块**
   - 识别任务列表页
   - 识别任务详情页
   - 草稿编辑页（核心功能）
   - 支持从识别结果批量入库

3. **图片管理模块**
   - 图片列表页
   - 图片上传组件
   - 图片预览

4. **整卷/资料源模块**
   - 整卷列表页
   - 整卷详情页
   - 扫码查卷页面
   - 新建整卷表单

### 中优先级
5. **答案管理模块**
   - 答案编辑页
   - AI 生成答案功能

6. **组卷和导出模块**
   - 组卷列表页
   - 组卷编辑页（拖拽排序）
   - 组卷预览页
   - 导出任务列表页

7. **归档容器模块**
   - 归档容器列表页
   - 归档容器详情页

8. **做题记录模块**
   - 做题记录列表页
   - 做题界面

### 低优先级
9. **管理员功能模块**
   - 用户管理页
   - 邀请码管理页
   - API 日志查看页

10. **高级功能**
    - LaTeX 公式渲染
    - Markdown 编辑器
    - 图片裁剪
    - 批量导入导出
    - 数据统计图表

## 安装和运行

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env.local` 并配置：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-here
```

### 3. 运行开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 4. 构建生产版本

```bash
npm run build
npm start
```

## API 接口约定

所有 API 请求都通过 `@/lib/api` 中的模块进行，遵循以下约定：

- 基础 URL: `process.env.NEXT_PUBLIC_API_URL`
- API 前缀: `/api/v1`
- 认证方式: `Authorization: Bearer <token>`
- 错误处理: 统一在 Axios 拦截器中处理
- 响应格式: 遵循后端 API 文档

## 核心业务流程

### 识别入库流程
1. 上传图片 → `/dashboard/images`
2. 创建识别任务 → `/dashboard/extractions`
3. 查看识别结果 → 识别任务详情页
4. 编辑草稿 → 草稿编辑页
5. 确认入库 → 调用 `extractionsApi.confirmQuestions()`

### 扫码查卷流程
1. 扫码获取 qr_code → `/dashboard/papers/scan`
2. 查找整卷 → `papersApi.getByQrCode()`
3. 查看题目 → 整卷详情页

### 组卷导出流程
1. 创建组卷 → `/dashboard/paper-sets/new`
2. 添加题目 → 组卷编辑页
3. 预览 → 组卷预览页
4. 创建导出 → `exportsApi.create()`
5. 下载 → 导出详情页

## 注意事项

1. **题目与答案分离**
   - 题目和答案必须分开管理
   - 答案通过 `/questions/{id}/answer` 端点操作

2. **识别任务草稿**
   - `DraftQuestion` 不是正式题目
   - 必须通过 `confirmQuestions` 才能入库

3. **权限控制**
   - 普通用户只能访问自己的数据
   - 管理员可以访问全量数据
   - 前端需要配合后端进行权限验证

4. **文件上传**
   - 使用 S3 预签名 URL
   - 先获取 upload URL，再上传到 S3
   - 最后创建图片记录

5. **UUID 处理**
   - 所有 UUID 字段使用 string 类型
   - 前端不负责生成 UUID

## 依赖说明

### 核心依赖
- `next`: React 框架
- `react`: UI 库
- `typescript`: 类型系统
- `@tanstack/react-query`: 数据请求和缓存
- `react-hook-form`: 表单管理
- `zod`: 表单验证
- `axios`: HTTP 客户端
- `zustand`: 状态管理

### UI 组件
- `tailwindcss`: 样式框架
- `@radix-ui/*`: 无样式的可访问组件
- `lucide-react`: 图标库
- `class-variance-authority`: 组件变体管理
- `clsx`: 条件类名
- `tailwind-merge`: 合并 Tailwind 类名

## 开发建议

1. **遵循单一职责原则**
   - 页面组件负责布局和数据获取
   - 业务逻辑抽取到自定义 Hook
   - 可复用逻辑抽取到工具函数

2. **组件分层**
   - `page.tsx`: 页面入口，负责路由和布局
   - 组件: UI 展示和交互
   - Hook: 业务逻辑和状态管理
   - API: 数据请求

3. **错误处理**
   - 使用 TanStack Query 的 error 状态
   - 统一的错误提示组件
   - 网络错误友好提示

4. **性能优化**
   - 利用 TanStack Query 的缓存机制
   - 图片懒加载
   - 列表虚拟化（大数据量）

5. **测试**
   - 组件测试（Jest + React Testing Library）
   - E2E 测试（Playwright）
   - API Mock（MSW）

## 常见问题

### Q: 如何添加新的 UI 组件？
A: 使用 shadcn/ui CLI:
```bash
npx shadcn-ui@latest add [component-name]
```

### Q: 如何处理文件上传？
A: 参考 `imagesApi.getUploadUrl()` 和 `imagesApi.uploadToS3()`

### Q: 如何实现权限控制？
A: 使用 middleware 或在页面组件中检查 `user.role`

### Q: 如何添加新的 API 端点？
A: 在 `src/lib/api/` 中创建对应的模块文件

## 贡献指南

1. 遵循现有代码风格
2. 使用 TypeScript 类型
3. 添加适当的注释
4. 保持组件简单和可复用
5. 编写清晰的提交信息

## 许可证

MIT
