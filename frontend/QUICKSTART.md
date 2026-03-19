# 快速启动指南

## 前置要求

- Node.js 18+ 和 npm
- 后端服务运行在 http://localhost:8000

## 安装步骤

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 环境变量配置

`.env.local` 文件已配置，内容如下：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=chenhaokai2004
NEXT_PUBLIC_APP_NAME=Question Bank
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### 3. 启动开发服务器

```bash
npm run dev
```

服务器将在 http://localhost:3000 启动

## 项目结构

```
frontend/
├── src/
│   ├── app/                    # Next.js 页面
│   │   ├── dashboard/          # 主应用页面
│   │   ├── login/              # 登录页
│   │   ├── register/           # 注册页
│   │   └── globals.css         # 全局样式
│   ├── components/
│   │   ├── ui/                 # shadcn/ui 组件
│   │   ├── layout/             # 布局组件
│   │   └── providers/          # Providers
│   ├── lib/
│   │   ├── api/                # API 客户端（11 个模块）
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── store/              # Zustand 状态管理
│   │   └── utils.ts            # 工具函数
│   └── types/                  # TypeScript 类型
```

## 功能模块

### 已完成 ✅

1. **认证系统**
   - 登录/注册页面
   - JWT 认证
   - 路由保护

2. **仪表盘**
   - 统计概览
   - 快速操作

3. **API 层**
   - 完整的 API 客户端封装
   - 所有业务模块的 API

4. **类型系统**
   - 完整的 TypeScript 类型定义
   - Zod 表单验证

### 待开发 🚧

1. **题库管理** - 题目的增删改查
2. **识别任务** - AI 识别和草稿编辑
3. **图片管理** - 图片上传和管理
4. **整卷管理** - 资料源和扫码查卷
5. **答案管理** - 答案编辑和 AI 生成
6. **组卷导出** - 组卷和导出功能
7. **归档容器** - 题单和错题本
8. **做题记录** - 历史记录查看

## 开发指南

### 添加新页面

1. 在 `src/app/dashboard/` 创建对应的文件夹和 `page.tsx`
2. 使用 `Header` 组件设置页面标题
3. 使用 `useQuery` 和 `useMutation` 进行数据操作

示例：

```tsx
'use client'

import { Header } from '@/components/layout/header'

export default function NewFeaturePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="新功能" subtitle="功能描述" />
      <div className="p-6">
        {/* 页面内容 */}
      </div>
    </div>
  )
}
```

### 使用 API

所有 API 都在 `@/lib/api` 中，使用 TanStack Query 进行数据请求：

```tsx
import { useQuery, useMutation } from '@tanstack/react-query'
import { questionsApi } from '@/lib/api'

// 获取数据
const { data, isLoading } = useQuery({
  queryKey: ['questions'],
  queryFn: () => questionsApi.list({ page: 1, pageSize: 20 }),
})

// 修改数据
const mutation = useMutation({
  mutationFn: questionsApi.create,
  onSuccess: () => {
    // 成功处理
  },
})
```

### 表单处理

使用 React Hook Form + Zod：

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { questionSchema, type QuestionFormValues } from '@/types/forms'

const {
  register,
  handleSubmit,
  formState: { errors },
} = useForm<QuestionFormValues>({
  resolver: zodResolver(questionSchema),
})

const onSubmit = (data: QuestionFormValues) => {
  // 处理表单提交
}
```

## 常见问题

### Q: 如何添加新的 shadcn/ui 组件？

```bash
npx shadcn-ui@latest add [component-name]
```

### Q: 如何调试 API 请求？

打开浏览器开发者工具 → Network 标签，查看请求详情。

### Q: 如何查看当前用户信息？

```tsx
import { useAuth } from '@/lib/hooks/use-auth'

const { user } = useAuth()
console.log(user)
```

### Q: 如何显示提示信息？

```tsx
import { useToast } from '@/lib/hooks/use-toast'

const { toast } = useToast()

toast({
  title: "成功",
  description: "操作已完成",
})
```

## 技术栈

- **框架**: Next.js 14.2 (App Router)
- **语言**: TypeScript 5.6
- **样式**: Tailwind CSS 3.4
- **组件**: shadcn/ui
- **状态**: Zustand 4.5
- **数据请求**: TanStack Query 5.28
- **表单**: React Hook Form 7.51 + Zod 3.22
- **HTTP**: Axios 1.6

## 下一步

1. 启动后端服务（确保运行在 8000 端口）
2. 启动前端开发服务器
3. 访问 http://localhost:3000
4. 注册账号（需要邀请码）
5. 开始开发具体功能模块

## 注意事项

- 所有 API 请求都需要认证（登录/注册页面除外）
- 题目和答案必须分开管理
- 识别任务需要先编辑草稿，再确认入库
- 文件上传使用 S3 预签名 URL
- 管理员功能只对 ADMIN 角色可见
