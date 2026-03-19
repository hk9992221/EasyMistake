'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search, Layers, FolderOpen } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/lib/api'
import Link from 'next/link'

export default function AdminPaperSetsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)

  const { data: paperSetsData, isLoading } = useQuery({
    queryKey: ['admin-paper-sets', currentPage, searchQuery],
    queryFn: () => adminApi.listAllPaperSets({
      page: currentPage,
      page_size: 20,
      search: searchQuery || undefined,
    }),
  })

  const paperSets = paperSetsData?.items || []
  const totalPages = paperSetsData?.total_pages || 1

  return (
    <div className="p-8">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold">总组卷管理</h1>
        <p className="text-muted-foreground">管理系统中的所有组卷</p>
      </div>

      {/* 搜索框 */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索组卷标题..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* 统计信息 */}
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总组卷数</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{paperSetsData?.total || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总题目数</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {paperSets.reduce((sum: number, set: any) => sum + (set.item_count || 0), 0)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均题数</CardTitle>
            <Badge variant="secondary">Avg</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {paperSets.length > 0
                ? Math.round(
                    paperSets.reduce((sum: number, set: any) => sum + (set.item_count || 0), 0) /
                      paperSets.length
                  )
                : 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 组卷列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">加载中...</div>
        </div>
      ) : paperSets.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <p className="text-muted-foreground">暂无组卷</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>组卷列表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {paperSets.map((set: any) => (
                <div
                  key={set.id}
                  className="flex items-start justify-between rounded-lg border p-4"
                >
                  <div className="flex-1">
                    <div className="mb-2 flex items-center gap-2">
                      <h3 className="font-medium">{set.title}</h3>
                      {set.created_by && (
                        <Badge variant="outline">创建者: {set.created_by}</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {set.item_count || 0} 道题目 · ID: {set.id}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      创建于 {new Date(set.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="ml-4 flex gap-2">
                    <Link href={`/dashboard/paper-sets/${set.id}`}>
                      <Button variant="outline" size="sm">
                        查看
                      </Button>
                    </Link>
                    <Button variant="ghost" size="sm" className="text-destructive">
                      删除
                    </Button>
                  </div>
                </div>
              ))}
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
    </div>
  )
}
