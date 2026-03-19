'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { FileQuestion } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '@/lib/api'
import { LatexContent } from '@/components/latex-content'
import { QuickFilterBar, QuickFilterData } from '@/components/quick-filter-bar'

export default function AdminQuestionsPage() {
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
  const [userKeyword, setUserKeyword] = useState('')
  const [currentPage, setCurrentPage] = useState(1)

  useEffect(() => {
    setCurrentPage(1)
  }, [filters, userKeyword])

  const { data: questionsData, isLoading } = useQuery({
    queryKey: ['admin-questions', currentPage, filters, userKeyword],
    queryFn: () =>
      adminApi.listAllQuestions({
        page: currentPage,
        page_size: 50,
        q: filters.searchQuery || undefined,
        subject: filters.subject || undefined,
        type: filters.type && filters.type !== 'all' ? filters.type : undefined,
        difficulty: filters.difficulty && filters.difficulty !== 'all' ? filters.difficulty : undefined,
        knowledge_point_q: filters.knowledgePointRegex || undefined,
        book_name: filters.bookName || undefined,
        chapter_name: filters.chapterName || undefined,
        tags_json: filters.selectedTags.length > 0 ? filters.selectedTags : undefined,
        start_date: filters.startDate || undefined,
        end_date: filters.endDate || undefined,
        user: userKeyword || undefined,
      }),
  })

  const questions = questionsData?.items || []
  const pageSize = questionsData?.page_size || 50
  const totalPages = Math.max(1, Math.ceil((questionsData?.total || 0) / pageSize))

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">总试题管理</h1>
        <p className="text-muted-foreground">管理系统中的所有试题</p>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-1">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总题目</CardTitle>
            <FileQuestion className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{questionsData?.total || 0}</div>
          </CardContent>
        </Card>
      </div>

      <div className="mb-6 space-y-3">
        <QuickFilterBar filters={filters} onChange={setFilters} />
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium">按用户筛选（邮箱或用户ID）</label>
                <Input
                  placeholder="例如：admin@example.com 或 UUID"
                  value={userKeyword}
                  onChange={(e) => setUserKeyword(e.target.value)}
                />
              </div>
              <div className="flex items-end">
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    setUserKeyword('')
                    setCurrentPage(1)
                  }}
                >
                  清空用户筛选
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-muted-foreground">加载中...</div>
        </div>
      ) : questions.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <p className="text-muted-foreground">暂无题目</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>题目列表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {questions.map((question: any) => (
                <div
                  key={question.id}
                  className="flex items-start justify-between rounded-lg border p-4"
                >
                  <div className="flex-1">
                    <div className="mb-2 flex flex-wrap gap-2">
                      {question.subject && <Badge variant="secondary">{question.subject}</Badge>}
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
                        <Badge variant="outline">
                          {question.type === 'MCQ'
                            ? '选择题'
                            : question.type === 'FILL_BLANK'
                            ? '填空题'
                            : question.type === 'SHORT_ANSWER'
                            ? '简答题'
                            : question.type === 'COMPUTATION'
                            ? '计算题'
                            : question.type}
                        </Badge>
                      )}
                      <Badge variant="outline">创建者: {question.created_by || question.user_id}</Badge>
                    </div>
                    <LatexContent
                      text={question.stem_latex || question.stem_text || ''}
                      className="line-clamp-2 text-sm whitespace-pre-wrap"
                    />
                    <p className="mt-2 text-xs text-muted-foreground">
                      ID: {question.id} · 创建于 {new Date(question.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="ml-4 flex gap-2">
                    <Link href={`/dashboard/questions/${question.id}`}>
                      <Button variant="outline" size="sm">
                        查看
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>

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
