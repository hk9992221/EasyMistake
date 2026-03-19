'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Search, History, DollarSign, TrendingUp, User } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/lib/api'

export default function AdminApiLogsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [viewMode, setViewMode] = useState<'logs' | 'users'>('logs')

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['admin-api-logs', currentPage, searchQuery],
    queryFn: () => adminApi.listApiLogs({
      page: currentPage,
      page_size: 50,
      search: searchQuery || undefined,
    }),
  })

  const logs = logsData?.items || []
  const totalPages = logsData?.total_pages || 1

  // 计算统计数据
  const totalTokens = logs.reduce((sum: number, log: any) => sum + (log.total_tokens || 0), 0)
  const totalCost = logs.reduce((sum: number, log: any) => sum + (log.cost_usd || 0), 0)
  const totalPromptTokens = logs.reduce((sum: number, log: any) => sum + (log.prompt_tokens || 0), 0)
  const totalCompletionTokens = logs.reduce((sum: number, log: any) => sum + (log.completion_tokens || 0), 0)

  // 按用户统计
  const userStats = logs.reduce((acc: Record<string, {
    email: string
    total_calls: number
    total_tokens: number
    total_cost: number
    prompt_tokens: number
    completion_tokens: number
  }>, log: any) => {
    const email = log.user_email || 'Unknown'
    if (!acc[email]) {
      acc[email] = {
        email,
        total_calls: 0,
        total_tokens: 0,
        total_cost: 0,
        prompt_tokens: 0,
        completion_tokens: 0
      }
    }
    acc[email].total_calls += 1
    acc[email].total_tokens += log.total_tokens || 0
    acc[email].total_cost += log.cost_usd || 0
    acc[email].prompt_tokens += log.prompt_tokens || 0
    acc[email].completion_tokens += log.completion_tokens || 0
    return acc
  }, {})

  const userStatsArray = Object.values(userStats).sort((a, b) => b.total_cost - a.total_cost)

  return (
    <div className="p-8">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">API 使用日志</h1>
        <p className="text-muted-foreground">查看系统 API 调用记录和成本统计</p>
      </div>

      {/* 统计信息 */}
      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总调用次数</CardTitle>
            <History className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{logsData?.total || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              API 调用总数
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总 Token 使用</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTokens.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">
              输入: {totalPromptTokens.toLocaleString()} / 输出: {totalCompletionTokens.toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总花费</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">¥{totalCost.toFixed(4)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              CNY（人民币）
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均成本</CardTitle>
            <Badge variant="secondary">Avg</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {logs.length > 0 ? `¥${(totalCost / logs.length).toFixed(6)}` : '¥0.000000'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              每次调用平均成本
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 筛选区域 */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索日志..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">视图模式:</span>
                <Select value={viewMode} onValueChange={(value: any) => setViewMode(value)}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="logs">日志列表</SelectItem>
                    <SelectItem value="users">用户统计</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 内容区域 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">加载中...</div>
        </div>
      ) : logs.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <p className="text-muted-foreground">暂无日志</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 日志列表视图 */}
          {viewMode === 'logs' && (
            <Card>
              <CardHeader>
                <CardTitle>API 调用日志</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="pb-3 text-left font-medium">时间</th>
                        <th className="pb-3 text-left font-medium">用户</th>
                        <th className="pb-3 text-left font-medium">用途</th>
                        <th className="pb-3 text-left font-medium">模型</th>
                        <th className="pb-3 text-left font-medium">Token 使用</th>
                        <th className="pb-3 text-left font-medium">成本 (CNY)</th>
                        <th className="pb-3 text-left font-medium">延迟</th>
                        <th className="pb-3 text-left font-medium">状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((log: any) => (
                        <tr key={log.id} className="border-b">
                          <td className="py-3">
                            {new Date(log.created_at).toLocaleString()}
                          </td>
                          <td className="py-3">{log.user_email || '-'}</td>
                          <td className="py-3">
                            <Badge variant="outline">{log.purpose || 'Unknown'}</Badge>
                          </td>
                          <td className="py-3">
                            <Badge variant="secondary">{log.model_name || 'Unknown'}</Badge>
                          </td>
                          <td className="py-3">
                            <div className="text-xs">
                              <div>总计: <span className="font-medium">{log.total_tokens || 0}</span></div>
                              {log.prompt_tokens !== null && log.completion_tokens !== null && (
                                <div className="text-muted-foreground">
                                  输入: {log.prompt_tokens} / 输出: {log.completion_tokens}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="py-3 font-medium">
                            ¥{(log.cost_usd || 0).toFixed(6)}
                          </td>
                          <td className="py-3">
                            {log.latency_ms ? `${log.latency_ms}ms` : '-'}
                          </td>
                          <td className="py-3">
                            <Badge
                              variant={log.status_code === 200 ? 'default' : 'destructive'}
                            >
                              {log.status_code || 'unknown'}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* 分页 */}
                {totalPages > 1 && (
                  <div className="mt-6 flex items-center justify-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      上一页
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      第 {currentPage} / {totalPages} 页
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      下一页
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 用户统计视图 */}
          {viewMode === 'users' && (
            <Card>
              <CardHeader>
                <CardTitle>用户 API 使用统计</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="pb-3 text-left font-medium">用户</th>
                        <th className="pb-3 text-left font-medium">调用次数</th>
                        <th className="pb-3 text-left font-medium">总 Token 使用</th>
                        <th className="pb-3 text-left font-medium">总成本 (CNY)</th>
                        <th className="pb-3 text-left font-medium">平均成本</th>
                      </tr>
                    </thead>
                    <tbody>
                      {userStatsArray.map((stat: any) => (
                        <tr key={stat.email} className="border-b">
                          <td className="py-3">
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium">{stat.email}</span>
                            </div>
                          </td>
                          <td className="py-3">
                            <Badge variant="outline">{stat.total_calls}</Badge>
                          </td>
                          <td className="py-3">
                            <div className="text-xs">
                              <div>总计: <span className="font-medium">{stat.total_tokens.toLocaleString()}</span></div>
                              <div className="text-muted-foreground">
                                输入: {stat.prompt_tokens.toLocaleString()} / 输出: {stat.completion_tokens.toLocaleString()}
                              </div>
                            </div>
                          </td>
                          <td className="py-3 font-medium">
                            ¥{stat.total_cost.toFixed(4)}
                          </td>
                          <td className="py-3 text-xs">
                            ¥{stat.total_calls > 0 ? (stat.total_cost / stat.total_calls).toFixed(6) : '0.000000'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
