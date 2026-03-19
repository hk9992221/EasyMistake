'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft, Plus } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { paperSetsApi } from '@/lib/api'
import { QuickFilterBar, QuickFilterData } from '@/components/quick-filter-bar'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { LatexContent } from '@/components/latex-content'
import { useQuery } from '@tanstack/react-query'
import { questionsApi, questionProgressApi } from '@/lib/api'
import { useMemo } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export default function NewPaperSetPage() {
  const router = useRouter()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [subject, setSubject] = useState('')
  const [outputFormat, setOutputFormat] = useState('MARKDOWN')
  const [selectedQuestions, setSelectedQuestions] = useState<Set<string>>(new Set())

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

  // 获取学习进度用于计算掌握度
  const questionsFromApi = questionsData?.items || []
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

  // 计算掌握度并应用筛选
  const { questions: filteredQuestions, masteryMap } = useMemo(() => {
    const map = new Map<string, number>()
    const filtered: any[] = []

    allProgress.forEach(({ questionId, progress }: any) => {
      if (!progress) {
        map.set(questionId, 0)
        return
      }
      map.set(questionId, Number(progress.proficiency_score || 0))
    })

    questionsFromApi.forEach((question: any) => {
      const mastery = map.get(question.id) ?? 0

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
  const totalPages = questionsData?.total_pages || questionsData?.totalPages || 1

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!title.trim()) {
        throw new Error('请输入组卷标题')
      }
      if (selectedQuestions.size === 0) {
        throw new Error('请至少选择一道题目')
      }

      // 创建组卷
      const paperSet = await paperSetsApi.create({
        title: title.trim(),
        subject: subject || undefined,
        description: description || undefined,
        output_format: outputFormat as any,
      })

      // 批量添加题目
      const items = Array.from(selectedQuestions).map((questionId, index) => ({
        question_id: questionId,
        order_index: index + 1,
      }))

      await paperSetsApi.batchAddItems(paperSet.id, items)

      return paperSet
    },
    onSuccess: (paperSet) => {
      router.push(`/dashboard/paper-sets/${paperSet.id}`)
    },
    onError: (error: any) => {
      alert(error.message || '创建组卷失败')
    },
  })

  const toggleQuestionSelection = (questionId: string) => {
    const newSelected = new Set(selectedQuestions)
    if (newSelected.has(questionId)) {
      newSelected.delete(questionId)
    } else {
      newSelected.add(questionId)
    }
    setSelectedQuestions(newSelected)
  }

  const isAllSelected = questions.length > 0 && questions.every((q: any) => selectedQuestions.has(q.id))
  const isPartiallySelected = questions.some((q: any) => selectedQuestions.has(q.id)) && !isAllSelected

  const toggleSelectAll = () => {
    const allQuestionIds = new Set(questions.map((q: any) => q.id))
    if (questions.every((q: any) => selectedQuestions.has(q.id))) {
      const newSelected = new Set(selectedQuestions)
      questions.forEach((q: any) => newSelected.delete(q.id))
      setSelectedQuestions(newSelected)
    } else {
      setSelectedQuestions(new Set([...Array.from(selectedQuestions), ...Array.from(allQuestionIds)]))
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-6xl mx-auto">
        {/* 顶部操作栏 */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold">创建新组卷</h1>
              <p className="text-muted-foreground">设置组卷信息并选择题目</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {/* 左侧：组卷设置 */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>组卷信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="title">标题 *</Label>
                  <Input
                    id="title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="输入组卷标题"
                  />
                </div>
                <div>
                  <Label htmlFor="subject">学科</Label>
                  <Input
                    id="subject"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="输入学科"
                  />
                </div>
                <div>
                  <Label htmlFor="description">描述</Label>
                  <Textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="输入组卷描述"
                    rows={3}
                  />
                </div>
                <div>
                  <Label htmlFor="format">输出格式</Label>
                  <Select value={outputFormat} onValueChange={setOutputFormat}>
                    <SelectTrigger id="format">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MARKDOWN">Markdown</SelectItem>
                      <SelectItem value="LATEX">LaTeX</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>已选题目 ({selectedQuestions.size})</CardTitle>
              </CardHeader>
              <CardContent>
                <Button
                  className="w-full"
                  size="lg"
                  onClick={() => createMutation.mutate()}
                  disabled={createMutation.isPending || !title.trim() || selectedQuestions.size === 0}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  {createMutation.isPending ? '创建中...' : '创建组卷'}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* 右侧：题目选择 */}
          <div className="col-span-2 space-y-6">
            <QuickFilterBar filters={filters} onChange={setFilters} />

            {isLoading ? (
              <Card>
                <CardContent className="py-12">
                  <div className="text-center text-muted-foreground">加载中...</div>
                </CardContent>
              </Card>
            ) : questions.length === 0 ? (
              <Card>
                <CardContent className="py-12">
                  <div className="text-center text-muted-foreground">
                    {questionsFromApi.length === 0 ? '暂无题目' : '没有符合筛选条件的题目'}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <>
                <div className="flex items-center gap-4 rounded-lg border bg-card p-3 text-sm font-medium text-muted-foreground">
                  <div className="w-10 text-center">
                    <Checkbox
                      checked={isPartiallySelected ? "indeterminate" : isAllSelected}
                      onCheckedChange={toggleSelectAll}
                    />
                  </div>
                  <div className="flex-1">题目</div>
                  <div className="w-24 text-center">掌握度</div>
                </div>

                <div className="space-y-3">
                  {questions.map((question: any) => {
                    const mastery = masteryMap.get(question.id) ?? 0
                    return (
                      <div
                        key={question.id}
                        className={`flex items-center gap-4 rounded-lg border bg-card p-3 transition-colors hover:bg-accent cursor-pointer ${
                          selectedQuestions.has(question.id) ? 'border-primary' : ''
                        }`}
                        onClick={() => toggleQuestionSelection(question.id)}
                      >
                        <div className="w-10 text-center">
                          <Checkbox
                            checked={selectedQuestions.has(question.id)}
                            onCheckedChange={() => toggleQuestionSelection(question.id)}
                          />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            {question.subject && (
                              <Badge variant="secondary" className="text-xs">{question.subject}</Badge>
                            )}
                            {question.difficulty && (
                              <Badge variant="outline" className="text-xs">{question.difficulty}</Badge>
                            )}
                          </div>
                          <LatexContent
                            text={question.stem_latex || question.stem_text || '无内容'}
                            className="text-sm"
                          />
                        </div>
                        <div className="w-24 text-center text-sm">
                          <span className={
                            mastery >= 80 ? 'text-green-600 font-medium' :
                            mastery >= 60 ? 'text-yellow-600 font-medium' :
                            'text-red-600 font-medium'
                          }>
                            {mastery}%
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* 分页 */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2">
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
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
