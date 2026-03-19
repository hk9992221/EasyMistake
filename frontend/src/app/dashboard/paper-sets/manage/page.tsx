'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, ExternalLink, Pencil, Search, Trash2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { paperSetsApi } from '@/lib/api'
import { LatexContent } from '@/components/latex-content'
import { getQuestionTypeLabel } from '@/lib/question-type'

function escapeRegex(input: string) {
  return input.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function buildMultiKeywordRegex(input: string) {
  const words = input
    .split(/\s+/)
    .map((w) => w.trim())
    .filter(Boolean)
  if (words.length === 0) return ''
  return words.map((w) => `(?=.*${escapeRegex(w)})`).join('') + '.*'
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function buildQuestionSource(question: any) {
  if (question?.source_anchor) return question.source_anchor
  const parts = [question?.book_name, question?.chapter_name].filter(Boolean)
  const base = parts.length > 0 ? parts.join(' / ') : '未知来源'
  return question?.page_no ? `${base} / 第${question.page_no}页` : base
}

export default function PaperSetManagePage() {
  const queryClient = useQueryClient()

  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 20

  const [search, setSearch] = useState('')
  const [nameRegex, setNameRegex] = useState('')
  const [multiKeywords, setMultiKeywords] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [expandedPaperSetId, setExpandedPaperSetId] = useState<string | null>(null)

  const generatedRegex = useMemo(() => buildMultiKeywordRegex(multiKeywords), [multiKeywords])
  const effectiveRegex = (nameRegex || generatedRegex || '').trim()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['paper-sets-manage', currentPage, pageSize, search, effectiveRegex, startDate, endDate],
    queryFn: () =>
      paperSetsApi.list({
        page: currentPage,
        page_size: pageSize,
        search: search.trim() || undefined,
        name_regex: effectiveRegex || undefined,
        start_date: startDate ? `${startDate}T00:00:00` : undefined,
        end_date: endDate ? `${endDate}T23:59:59` : undefined,
      }),
  })

  const { data: previewData, isLoading: isPreviewLoading } = useQuery({
    queryKey: ['paper-set-preview-manage', expandedPaperSetId],
    queryFn: () => paperSetsApi.preview(expandedPaperSetId as string),
    enabled: Boolean(expandedPaperSetId),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => paperSetsApi.delete(id),
    onSuccess: async (_, id) => {
      if (expandedPaperSetId === id) setExpandedPaperSetId(null)
      await queryClient.invalidateQueries({ queryKey: ['paper-sets-manage'] })
    },
  })

  const paperSets = data?.items || []
  const totalPages = data?.total_pages || data?.totalPages || 1
  const previewQuestions = previewData?.questions || []

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">试卷管理</h1>
          <p className="text-muted-foreground">搜索试卷、进入批改、查看题目来源和题号。</p>
        </div>
        <Link href="/dashboard/paper-sets/new">
          <Button>新建组卷</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            筛选条件
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              placeholder="搜索（支持组卷ID / 标题关键词）"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setCurrentPage(1)
              }}
            />
            <Input
              placeholder='名称正则（例：.*数学.*期中.*）'
              value={nameRegex}
              onChange={(e) => {
                setNameRegex(e.target.value)
                setCurrentPage(1)
              }}
            />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              placeholder="多关键词（空格分隔，如：数学 期中 八年级）"
              value={multiKeywords}
              onChange={(e) => {
                setMultiKeywords(e.target.value)
                setCurrentPage(1)
              }}
            />
            <div className="rounded-md border px-3 py-2 text-sm text-muted-foreground">
              自动正则：{generatedRegex || '-'}
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value)
                setCurrentPage(1)
              }}
            />
            <Input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value)
                setCurrentPage(1)
              }}
            />
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">加载中...</div>
      ) : isError ? (
        <Card>
          <CardContent className="py-6 text-sm text-destructive">
            查询失败，请检查筛选条件或重试。
          </CardContent>
        </Card>
      ) : paperSets.length === 0 ? (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">没有符合条件的组卷。</CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>组卷列表</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {paperSets.map((set: any) => {
              const isExpanded = expandedPaperSetId === set.id
              return (
                <div key={set.id} className="rounded-md border p-3 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link href={`/dashboard/paper-sets/${set.id}`} className="font-medium hover:underline">
                          {set.title}
                        </Link>
                        <Badge variant="outline">{set.item_count || 0} 题</Badge>
                        {set.subject && <Badge variant="secondary">{set.subject}</Badge>}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">ID: {set.id}</div>
                      <div className="mt-1 text-xs text-muted-foreground">创建时间：{formatDateTime(set.created_at)}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/dashboard/paper-sets/${set.id}/review`}>
                        <Button size="sm">进入批改</Button>
                      </Link>
                      <Link href={`/dashboard/paper-sets/${set.id}`}>
                        <Button size="sm" variant="outline">
                          <Pencil className="mr-1 h-3.5 w-3.5" />
                          编辑组卷
                        </Button>
                      </Link>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setExpandedPaperSetId(isExpanded ? null : set.id)}
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="mr-1 h-3.5 w-3.5" />
                            收起题目
                          </>
                        ) : (
                          <>
                            <ChevronDown className="mr-1 h-3.5 w-3.5" />
                            查看题目
                          </>
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={deleteMutation.isPending}
                        onClick={async () => {
                          const ok = window.confirm(`确认删除组卷「${set.title}」吗？`)
                          if (!ok) return
                          await deleteMutation.mutateAsync(set.id)
                        }}
                      >
                        <Trash2 className="mr-1 h-3.5 w-3.5" />
                        删除
                      </Button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="rounded-md border bg-muted/20 p-3">
                      {isPreviewLoading ? (
                        <div className="text-sm text-muted-foreground">题目加载中...</div>
                      ) : previewQuestions.length === 0 ? (
                        <div className="text-sm text-muted-foreground">该组卷暂无题目。</div>
                      ) : (
                        <div className="space-y-2">
                          {previewQuestions.map((q: any) => (
                            <div key={q.id} className="rounded-md border bg-background p-3">
                              <div className="flex flex-wrap items-center gap-2 text-xs">
                                <Badge variant="outline">第{q.order_index}题</Badge>
                                <Badge variant="secondary">{getQuestionTypeLabel(q.type)}</Badge>
                                <Badge variant="outline">题号：{q.question_no || '-'}</Badge>
                                <Badge variant="outline">分值：{q.score ?? '-'}</Badge>
                              </div>
                              <div className="mt-2 text-sm">
                                <LatexContent
                                  text={q.stem_latex || q.stem_text || '（无题干）'}
                                  className="line-clamp-3 whitespace-pre-wrap"
                                />
                              </div>
                              <div className="mt-2 text-xs text-muted-foreground">
                                来源：{buildQuestionSource(q)}
                              </div>
                              <div className="mt-2">
                                <Link
                                  href={`/dashboard/questions/${q.id}`}
                                  className="inline-flex items-center text-xs text-primary hover:underline"
                                >
                                  查看题目详情
                                  <ExternalLink className="ml-1 h-3 w-3" />
                                </Link>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-2">
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
