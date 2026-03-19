'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, FolderOpen, History, Settings } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { questionsApi, paperSetsApi, questionProgressApi } from '@/lib/api'
import { QuickFilterBar, QuickFilterData } from '@/components/quick-filter-bar'
import { LatexContent } from '@/components/latex-content'
import { getQuestionTypeLabel } from '@/lib/question-type'

const SELECTED_QUESTIONS_STORAGE_KEY = 'paper-sets-selected-questions'

export default function PaperSetsPage() {
  const router = useRouter()

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
  const [selectedQuestions, setSelectedQuestions] = useState<Set<string>>(new Set())

  // 从 localStorage 恢复选择的题目
  useEffect(() => {
    const saved = localStorage.getItem(SELECTED_QUESTIONS_STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setSelectedQuestions(new Set(parsed))
      } catch (e) {
        console.error('Failed to parse saved questions:', e)
      }
    }
  }, [])

  // 保存选择的题目到 localStorage
  useEffect(() => {
    localStorage.setItem(SELECTED_QUESTIONS_STORAGE_KEY, JSON.stringify(Array.from(selectedQuestions)))
  }, [selectedQuestions])

  // 获取题目列表
  const { data: questionsData, isLoading } = useQuery({
    queryKey: ['questions', currentPage, pageSize, filters],
    queryFn: () => questionsApi.list({
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

  // 获取现有组卷列表
  const { data: paperSetsData } = useQuery({
    queryKey: ['paper-sets'],
    queryFn: () => paperSetsApi.list({ page: 1, page_size: 100 }),
  })

  const questionsFromApi = questionsData?.items || []
  const totalPages = questionsData?.total_pages || questionsData?.totalPages || 1
  const paperSets = paperSetsData?.items || []

  // 获取当前页所有题目的学习进度
  const questionIds = questionsFromApi.map((q: any) => q.id)
  const { data: allProgress = [] } = useQuery({
    queryKey: ['question-progress', 'bulk', questionIds],
    queryFn: async () => {
      if (questionIds.length === 0) return []
      const progressPromises = questionIds.map((id: string) =>
        questionProgressApi.list({ page: 1, pageSize: 1, questionId: id }).catch(() => ({ items: [] as any[] }))
      )
      const results = await Promise.all(progressPromises)
      return questionIds.map((id: string, index: number) => ({
        questionId: id,
        progress: results[index]?.items?.[0] || null,
      }))
    },
    enabled: questionIds.length > 0,
  })

  // 计算每个题目的掌握度并应用筛选
  const { questions: filteredQuestions, masteryMap } = useMemo(() => {
    const map = new Map<string, number>()
    const filtered: any[] = []

    // 初始化所有题目的掌握度为0
    questionsFromApi.forEach((question: any) => {
      map.set(question.id, 0)
    })

    // 从progress数据中读取掌握度
    allProgress.forEach(({ questionId, progress }: any) => {
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
  }, [questionsFromApi, allProgress, filters.masteryLevel, filters.customMastery])

  const questions = filteredQuestions

  const toggleQuestionSelection = (questionId: string) => {
    const newSelected = new Set(selectedQuestions)
    if (newSelected.has(questionId)) {
      newSelected.delete(questionId)
    } else {
      newSelected.add(questionId)
    }
    setSelectedQuestions(newSelected)
  }

  const toggleSelectAll = () => {
    const allQuestionIds = new Set(questions.map((q: any) => q.id))
    // 如果当前页所有题目都已选中，则取消全选；否则全选
    if (questions.every((q: any) => selectedQuestions.has(q.id))) {
      // 取消全选当前页
      const newSelected = new Set(selectedQuestions)
      questions.forEach((q: any) => newSelected.delete(q.id))
      setSelectedQuestions(newSelected)
    } else {
      // 全选当前页
      setSelectedQuestions(new Set([...Array.from(selectedQuestions), ...Array.from(allQuestionIds)]))
    }
  }

  const isAllSelected = questions.length > 0 && questions.every((q: any) => selectedQuestions.has(q.id))
  const isPartiallySelected = questions.some((q: any) => selectedQuestions.has(q.id)) && !isAllSelected

  const handleCreatePaperSet = async () => {
    if (selectedQuestions.size === 0) {
      return
    }

    try {
      // 创建组卷
      const paperSet = await paperSetsApi.create({
        title: `新组卷 ${new Date().toLocaleDateString()}`,
        subject: filters.subject || undefined,
        output_format: 'MARKDOWN',
      })

      // 批量添加题目
      const items = Array.from(selectedQuestions).map((questionId, index) => ({
        question_id: questionId,
        order_index: index + 1,
      }))

      await paperSetsApi.batchAddItems(paperSet.id, items)

      // 清空选择并跳转到组卷详情页
      setSelectedQuestions(new Set())
      router.push(`/dashboard/paper-sets/${paperSet.id}`)
    } catch (error) {
      console.error('Failed to create paper set:', error)
      alert('创建组卷失败，请重试')
    }
  }

  return (
    <div className="flex h-full">
      {/* 左侧状态栏 */}
      <div className="w-64 border-r bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold">组卷</h2>
        <div className="space-y-4">
          <div className="sticky top-0 z-10 -mx-2 bg-card px-2 pb-3 pt-1">
            <Link href="/dashboard/paper-sets/manage">
              <Button variant="outline" className="mb-2 w-full gap-2">
                <Settings className="h-4 w-4" />
                组卷管理
              </Button>
            </Link>
            <Link href="/dashboard/paper-sets/new">
              <Button className="w-full gap-2">
                <Plus className="h-4 w-4" />
                新建组卷
              </Button>
            </Link>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">现有组卷</h3>
            <div className="space-y-2">
              {paperSets.length === 0 ? (
                <p className="text-sm text-muted-foreground">暂无组卷</p>
              ) : (
                paperSets.map((set: any) => (
                  <div
                    key={set.id}
                    className="group flex items-center gap-1 rounded-md p-2 hover:bg-accent transition-colors"
                  >
                    <Link
                      href={`/dashboard/paper-sets/${set.id}`}
                      className="min-w-0 flex-1"
                    >
                      <div className="flex items-center gap-2">
                        <FolderOpen className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{set.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {set.item_count || 0} 道题
                          </p>
                        </div>
                      </div>
                    </Link>
                    <Link
                      href={`/dashboard/paper-sets/${set.id}?exports=true`}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-accent rounded"
                      title="导出历史"
                    >
                      <History className="h-3.5 w-3.5 text-muted-foreground" />
                    </Link>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>

      {/* 右侧主内容区 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-8">
          {/* 页面标题 */}
          <div className="mb-6">
            <h1 className="text-2xl font-bold">组卷</h1>
            <p className="text-muted-foreground">选择题目创建试卷</p>
          </div>

          {/* 已选题目提示 */}
          {selectedQuestions.size > 0 && (
            <Card className="mb-6 border-primary">
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">已选择 {selectedQuestions.size} 道题目</p>
                  <p className="text-sm text-muted-foreground">
                    点击"创建组卷"按钮将选中的题目组卷
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedQuestions(new Set())}
                  >
                    清空选择
                  </Button>
                  <Button size="sm" onClick={handleCreatePaperSet}>
                    创建组卷
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 快速筛选栏 */}
          <QuickFilterBar filters={filters} onChange={setFilters} />

          {/* 题目列表 */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-muted-foreground">加载中...</div>
            </div>
          ) : questions.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <p className="text-muted-foreground">
                    {questionsFromApi.length === 0 ? '暂无题目' : '没有符合筛选条件的题目'}
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {/* 表头 */}
              <div className="flex items-center gap-4 rounded-lg border bg-card p-3 text-sm font-medium text-muted-foreground">
                <div className="w-10 text-center">
                  <Checkbox
                    checked={isPartiallySelected ? "indeterminate" : isAllSelected}
                    onCheckedChange={toggleSelectAll}
                  />
                </div>
                <div className="flex-1">题目</div>
                <div className="w-24 text-center">学科</div>
                <div className="w-24 text-center">难度</div>
                <div className="w-24 text-center">题型</div>
                <div className="w-24 text-center">掌握度</div>
              </div>

              {/* 题目行 */}
              {questions.map((question: any) => (
                <div
                  key={question.id}
                  className={`flex items-center gap-4 rounded-lg border bg-card p-3 transition-colors hover:bg-accent cursor-pointer ${
                    selectedQuestions.has(question.id) ? 'border-primary' : ''
                  }`}
                  onClick={(e) => {
                    // 阻止 checkbox 的点击事件触发跳转
                    if (!(e.target as HTMLElement).closest('input[type="checkbox"]')) {
                      router.push(`/dashboard/questions/${question.id}`)
                    }
                  }}
                >
                  <div className="w-10 text-center" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedQuestions.has(question.id)}
                      onCheckedChange={() => toggleQuestionSelection(question.id)}
                    />
                  </div>
                  <div className="flex-1">
                    <LatexContent
                      text={question.stem_latex || question.stem_text || question.content_text || question.content || '无内容'}
                      className="text-sm"
                    />
                  </div>
                  <div className="w-24 text-center">
                    {question.subject && (
                      <Badge variant="secondary" className="text-xs">
                        {question.subject}
                      </Badge>
                    )}
                  </div>
                  <div className="w-24 text-center">
                    {question.difficulty && (
                      <Badge
                        variant={
                          question.difficulty === 'EASY'
                            ? 'default'
                            : question.difficulty === 'MEDIUM'
                            ? 'secondary'
                            : 'destructive'
                        }
                        className="text-xs"
                      >
                        {question.difficulty === 'EASY'
                          ? '简单'
                          : question.difficulty === 'MEDIUM'
                          ? '中等'
                          : '困难'}
                      </Badge>
                    )}
                  </div>
                  <div className="w-24 text-center">
                    {question.type && (
                      <Badge variant="outline" className="text-xs">
                        {getQuestionTypeLabel(question.type)}
                      </Badge>
                    )}
                  </div>
                  <div className="w-24 text-center text-sm">
                    {masteryMap.has(question.id) ? (
                      <span className={
                        masteryMap.get(question.id)! >= 80 ? 'text-green-600 font-medium' :
                        masteryMap.get(question.id)! >= 60 ? 'text-yellow-600 font-medium' :
                        'text-red-600 font-medium'
                      }>
                        {masteryMap.get(question.id)}%
                      </span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </div>
                </div>
              ))}

              {/* 分页 */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-4">
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
                  <span className="text-sm text-muted-foreground">条</span>
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
