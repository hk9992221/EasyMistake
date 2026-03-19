'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, Filter, Plus } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { questionsApi, questionProgressApi } from '@/lib/api'
import { LatexContent } from '@/components/latex-content'
import { QuickFilterBar, QuickFilterData } from '@/components/quick-filter-bar'
import { getQuestionTypeLabel } from '@/lib/question-type'

export default function QuestionsPage() {
  const [filters, setFilters] = useState<QuickFilterData>({
    searchQuery: '',
    questionNo: '',
    subject: '',
    selectedTags: [],
    knowledgePointRegex: '',
    difficulty: 'all',
    type: 'all',
    bookName: '',
    chapterName: '',
    masteryLevel: 'all',
    customMastery: '',
    startDate: '',
    endDate: '',
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const { data: questionsData, isLoading } = useQuery({
    queryKey: [
      'questions',
      currentPage,
      pageSize,
      filters,
    ],
    queryFn: () =>
      questionsApi.list({
        page: currentPage,
        pageSize,
        q: filters.searchQuery || undefined,
        question_no: filters.questionNo || undefined,
        subject: filters.subject || undefined,
        tags_json: filters.selectedTags.length > 0 ? filters.selectedTags : undefined,
        knowledge_point_q: filters.knowledgePointRegex || undefined,
        difficulty: filters.difficulty !== 'all' ? filters.difficulty : undefined,
        type: filters.type !== 'all' ? filters.type : undefined,
        book_name: filters.bookName || undefined,
        chapter_name: filters.chapterName || undefined,
        start_date: filters.startDate ? `${filters.startDate}T00:00:00` : undefined,
        end_date: filters.endDate ? `${filters.endDate}T23:59:59` : undefined,
      }),
  })

  // 获取学习进度用于计算掌握度
  const questionsFromApi = questionsData?.items || []
  const questionIds = questionsFromApi.map((q: any) => q.id)

  const { data: progressData = [] } = useQuery<Array<{ questionId: string; progress: any | null }>>({
    queryKey: ['question-progress', 'bulk', questionIds],
    queryFn: async () => {
      if (questionIds.length === 0) return []
      const progressPromises = questionIds.map((id: string) =>
        questionProgressApi.list({ page: 1, pageSize: 1, questionId: id }).catch((err) => {
          console.error(`Failed to fetch progress for question ${id}:`, err)
          return { items: [] as any[] }
        })
      )
      const results = await Promise.all(progressPromises)
      return questionIds.map((id: string, index: number) => ({
        questionId: id,
        progress: results[index]?.items?.[0] || null,
      }))
    },
    enabled: questionIds.length > 0,
  })

  // 计算掌握度并筛选
  const { questions: filteredQuestions, masteryMap } = useMemo(() => {
    const map = new Map<string, number>()
    const filtered: any[] = []

    // 初始化所有题目的掌握度为0
    questionsFromApi.forEach((question: any) => {
      map.set(question.id, 0)
    })

    // 从progress数据计算掌握度
    progressData?.forEach(({ questionId, progress }: any) => {
      if (!progress) {
        map.set(questionId, 0)
        return
      }
      map.set(questionId, Number(progress.proficiency_score || 0))
    })

    questionsFromApi.forEach((question: any) => {
      const mastery = map.get(question.id) ?? 0

      // 掌握度筛选
      if (filters.masteryLevel !== 'all') {
        if (filters.masteryLevel === 'low' && mastery > 60) return
        if (filters.masteryLevel === 'medium' && mastery > 80) return
        if (filters.masteryLevel === 'high' && mastery <= 80) return
        if (filters.masteryLevel === 'custom') {
          const threshold = parseInt(filters.customMastery) || 0
          if (mastery > threshold) return
        }
      }

      filtered.push(question)
    })

    return { questions: filtered, masteryMap: map }
  }, [questionsFromApi, progressData, filters.masteryLevel, filters.customMastery])

  const totalPages = questionsData?.total_pages || questionsData?.totalPages || 1

  return (
    <div className="flex h-full">
      <div className="w-64 border-r bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold">题库</h2>
        <div className="space-y-4">
          <div>
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">统计</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>总数</span>
                <span className="font-medium">{questionsData?.total || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>当前页</span>
                <span className="font-medium">{filteredQuestions.length}</span>
              </div>
              {(filters.masteryLevel !== 'all' || filters.startDate || filters.endDate) && (
                <div className="flex justify-between">
                  <span>筛选后</span>
                  <span className="font-medium">{filteredQuestions.length}</span>
                </div>
              )}
            </div>
          </div>

          <div className="border-t pt-4">
            <Link href="/dashboard/extract">
              <Button className="w-full gap-2">
                <Plus className="h-4 w-4" />
                录入试题
              </Button>
            </Link>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-8">
          <div className="mb-6">
            <h1 className="text-2xl font-bold">试题列表</h1>
            <p className="text-muted-foreground">浏览和管理所有试题</p>
          </div>

          {/* 快速筛选栏 */}
          <QuickFilterBar filters={filters} onChange={setFilters} />

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-muted-foreground">加载中...</div>
            </div>
          ) : filteredQuestions.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <p className="text-muted-foreground">
                    {questionsFromApi.length === 0 ? '暂无试题' : '没有符合筛选条件的试题'}
                  </p>
                  <Link href="/dashboard/extract" className="mt-4 inline-block">
                    <Button>录入第一道试题</Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {filteredQuestions.map((question: any) => {
                const mastery = masteryMap.get(question.id) ?? 0
                return (
                  <Card key={question.id} className="hover:shadow-md transition-shadow">
                    <CardHeader>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="mb-2 flex flex-wrap gap-2">
                            {question.subject && (
                              <Badge variant="secondary">{question.subject}</Badge>
                            )}
                            {question.difficulty && (
                              <Badge
                                variant={
                                  question.difficulty === 'EASY'
                                    ? 'default'
                                    : question.difficulty === 'MEDIUM'
                                    ? 'secondary'
                                    : 'destructive'
                                }
                              >
                                {question.difficulty === 'EASY'
                                  ? '简单'
                                  : question.difficulty === 'MEDIUM'
                                  ? '中等'
                                  : '困难'}
                              </Badge>
                            )}
                            {question.type && (
                              <Badge variant="outline">{getQuestionTypeLabel(question.type)}</Badge>
                            )}
                            <Badge
                              variant={
                                mastery >= 80 ? 'default' :
                                mastery >= 60 ? 'secondary' :
                                'destructive'
                              }
                            >
                              掌握度: {mastery}%
                            </Badge>
                          </div>
                          <CardTitle className="text-base">
                            <LatexContent
                              text={question.stem_text || question.content_text || question.content || ''}
                              className="prose prose-sm max-w-none whitespace-pre-wrap max-h-16 overflow-hidden"
                            />
                          </CardTitle>
                        </div>
                        <Link href={`/dashboard/questions/${question.id}`}>
                          <Button variant="outline" size="sm">
                            查看
                          </Button>
                        </Link>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        ID: {question.id} · 创建于{' '}
                        {new Date(question.created_at).toLocaleDateString()}
                      </p>
                    </CardContent>
                  </Card>
                )
              })}

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">每页</span>
                  <Select
                    value={String(pageSize)}
                    onValueChange={(value) => {
                      setPageSize(Number(value))
                      setCurrentPage(1)
                    }}
                  >
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="20">20</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {totalPages > 1 && (
                  <div className="flex items-center gap-2">
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
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
