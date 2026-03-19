'use client'

import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/lib/hooks/use-auth'
import { analyticsApi, authApi, questionsApi, reviewsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  BookOpen,
  FileQuestion,
  FileText,
  History,
  Layers,
  CalendarClock,
  TrendingUp,
  Users,
  DollarSign,
} from 'lucide-react'

export default function DashboardPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'

  const { data: questionData } = useQuery({
    queryKey: ['dashboard-question-total'],
    queryFn: () => questionsApi.list({ page: 1, pageSize: 1 }),
  })

  const { data: analyticsOverview } = useQuery({
    queryKey: ['dashboard-analytics-overview'],
    queryFn: () => analyticsApi.overview(),
  })
  const { data: errorTagsStats } = useQuery({
    queryKey: ['dashboard-error-tags'],
    queryFn: () => analyticsApi.errorTags(5),
  })

  const { data: reviewToday } = useQuery({
    queryKey: ['dashboard-reviews-today'],
    queryFn: () => reviewsApi.getToday(),
  })

  const { data: costStats } = useQuery({
    queryKey: ['dashboard-cost-stats'],
    queryFn: () => authApi.getDashboard(),
  })

  const stats = {
    totalMistakes: analyticsOverview?.mistake_questions ?? 0,
    unmasteredMistakes: (analyticsOverview?.mistake_questions ?? 0) - (analyticsOverview?.mastered_questions ?? 0),
    dueToday: analyticsOverview?.due_today ?? reviewToday?.items?.length ?? 0,
    tokenUsage: costStats?.total_tokens ?? 0,
    cost: costStats?.total_cost_cny ?? costStats?.total_cost_usd ?? 0,
    totalQuestions: questionData?.total ?? 0,
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-bold">仪表盘</h1>
        <p className="mt-1 text-sm text-muted-foreground">查看核心统计与常用功能入口</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">快捷操作</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Link href="/dashboard/extract">
            <Button variant="outline" className="w-full justify-start gap-2">
              <BookOpen className="h-4 w-4" />
              录入试题
            </Button>
          </Link>
          <Link href="/dashboard/questions">
            <Button variant="outline" className="w-full justify-start gap-2">
              <FileText className="h-4 w-4" />
              试题管理
            </Button>
          </Link>
          <Link href="/dashboard/paper-sets">
            <Button variant="outline" className="w-full justify-start gap-2">
              <Layers className="h-4 w-4" />
              组卷
            </Button>
          </Link>
          <Link href="/dashboard/reviews">
            <Button variant="outline" className="w-full justify-start gap-2">
              <CalendarClock className="h-4 w-4" />
              今日复习
            </Button>
          </Link>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总错题数</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalMistakes}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">未掌握错题</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.unmasteredMistakes}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日待复习</CardTitle>
            <CalendarClock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.dueToday}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">花费金额</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">¥{stats.cost.toFixed(2)}</div>
            <div className="mt-1 text-xs text-muted-foreground">Token: {stats.tokenUsage}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">错因分析 Top 5</CardTitle>
        </CardHeader>
        <CardContent>
          {!errorTagsStats?.items?.length ? (
            <p className="text-sm text-muted-foreground">暂无错因数据，先在复习/做题时标注错因。</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
              {errorTagsStats.items.map((item) => (
                <div key={item.error_tag} className="rounded-md border p-3">
                  <div className="text-xs text-muted-foreground">{item.error_tag}</div>
                  <div className="text-xl font-semibold">{item.count}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">当前状态</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <span className="font-medium">用户：</span>
              {user?.email ?? '-'}
            </p>
            <p>
              <span className="font-medium">角色：</span>
              {isAdmin ? '管理员' : '普通用户'}
            </p>
            <p>
              <span className="font-medium">总题目：</span>
              {stats.totalQuestions}
            </p>
          </CardContent>
        </Card>

        {isAdmin && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">管理员功能</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Link href="/dashboard/admin/questions">
                <Button variant="ghost" className="w-full justify-start gap-2">
                  <FileQuestion className="h-4 w-4" />
                  总试题管理
                </Button>
              </Link>
              <Link href="/dashboard/admin/users">
                <Button variant="ghost" className="w-full justify-start gap-2">
                  <Users className="h-4 w-4" />
                  用户管理
                </Button>
              </Link>
              <Link href="/dashboard/admin/paper-sets">
                <Button variant="ghost" className="w-full justify-start gap-2">
                  <Layers className="h-4 w-4" />
                  总组卷管理
                </Button>
              </Link>
              <Link href="/dashboard/admin/api-logs">
                <Button variant="ghost" className="w-full justify-start gap-2">
                  <History className="h-4 w-4" />
                  API 使用日志
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
