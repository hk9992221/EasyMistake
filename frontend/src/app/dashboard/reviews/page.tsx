'use client'

import { invalidateLearning } from '@/lib/api/invalidate-learning'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { exportsApi, reviewsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LatexContent } from '@/components/latex-content'
import { useToast } from '@/lib/hooks/use-toast'

const ERROR_TAGS = [
  { code: 'KNOWLEDGE', name: '知识点不会' },
  { code: 'CONCEPT', name: '概念不清' },
  { code: 'METHOD', name: '方法不会' },
  { code: 'STRATEGY', name: '思路卡住' },
  { code: 'CALCULATION', name: '计算错误' },
  { code: 'CARELESS', name: '粗心' },
  { code: 'MISREAD', name: '审题错误' },
  { code: 'TIME_PRESSURE', name: '时间不够' },
]

const REVIEW_REASONS: Record<string, string> = {
  overdue_and_low_mastery: '已逾期，掌握程度较低',
  recent_wrong_answer: '最近一次答错',
  scheduled_review: '计划复习',
}

function errorMessage(error: unknown, fallback: string) {
  return error && typeof error === 'object' && 'message' in error && typeof error.message === 'string'
    ? error.message : fallback
}

type OptionItem = {
  key: string
  text: string
}

function parseMaybeJson(input: unknown): unknown {
  if (typeof input !== 'string') return input
  try {
    return JSON.parse(input)
  } catch {
    return input
  }
}

function normalizeOptions(contentJson: unknown): OptionItem[] {
  const data = parseMaybeJson(contentJson)
  if (!data || typeof data !== 'object') return []
  const raw = (data as Record<string, unknown>).options ?? (data as Record<string, unknown>).choices
  if (!Array.isArray(raw)) return []

  return raw
    .map((item, index) => {
      if (!item || typeof item !== 'object') return null
      const obj = item as Record<string, unknown>
      const key = String(obj.key ?? obj.label ?? String.fromCharCode(65 + index)).trim()
      const text = String(obj.text ?? obj.content ?? '').trim()
      if (!text) return null
      return { key, text }
    })
    .filter((item): item is OptionItem => Boolean(item))
}

export default function ReviewsPage() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [errorTagsMap, setErrorTagsMap] = useState<Record<string, string[]>>({})
  const [showFullQuestion, setShowFullQuestion] = useState(false)
  const [answerVisibleMap, setAnswerVisibleMap] = useState<Record<string, boolean>>({})
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [subject, setSubject] = useState<string | undefined>()

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reviews-today-page', page, pageSize, subject, showFullQuestion],
    queryFn: () => reviewsApi.getToday({
      page, page_size: pageSize, subject, include_details: showFullQuestion,
    }),
  })

  useEffect(() => {
    if (data && page > Math.max(1, data.total_pages)) setPage(Math.max(1, data.total_pages))
  }, [data, page])

  const completeMutation = useMutation({
    mutationFn: ({
      questionId,
      result,
      errorTags,
    }: {
      questionId: string
      result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED'
      errorTags?: string[]
    }) => reviewsApi.complete(questionId, { result, error_tags: errorTags || [] }),
    onSuccess: async (_data, variables) => {
      setErrorTagsMap((prev) => ({ ...prev, [variables.questionId]: [] }))
      setAnswerVisibleMap((prev) => ({ ...prev, [variables.questionId]: false }))
      await invalidateLearning(queryClient)
    },
    onError: () => {
      toast({ title: '提交失败', description: '请稍后重试', variant: 'destructive' })
    },
  })

  const generateDailySetMutation = useMutation({
    mutationFn: async () => {
      // Generate every due question matching the subject, across all pages.
      const paperSet = await reviewsApi.generateDailyPaperSet(subject)
      await queryClient.invalidateQueries({ queryKey: ['paper-sets'] })
      await queryClient.invalidateQueries({ queryKey: ['paper-set-preview', paperSet.paper_set_id] })

      const exportTask = await exportsApi.create({
        paper_set_id: paperSet.paper_set_id,
        format: 'LATEX_ZIP',
      })

      let current = exportTask
      const start = Date.now()
      while (Date.now() - start < 120000) {
        if (current.status === 'DONE') break
        if (current.status === 'FAILED') {
          throw new Error(current.error || '导出失败')
        }
        await new Promise((resolve) => setTimeout(resolve, 2000))
        current = await exportsApi.get(exportTask.id)
      }

      if (current.status !== 'DONE') {
        throw new Error('组卷已保存，导出仍在处理中，请到组卷管理的导出历史下载')
      }

      const blob = await exportsApi.download(current.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${paperSet.title}.tex.zip`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      return paperSet
    },
    onSuccess: (paperSet) => {
      toast({
        title: paperSet.reused ? '已更新并下载今日组卷' : '已生成并下载今日组卷',
        description: `共 ${paperSet.item_count} 题，LaTeX 导出完成`,
      })
    },
    onError: (error) => {
      toast({ title: '生成或导出失败', description: errorMessage(error, '请稍后重试'), variant: 'destructive' })
    },
  })

  const items = data?.items || []
  const total = data?.total || 0
  const subjects = Array.from(new Set([...(data?.subjects || []), ...(subject ? [subject] : [])]))

  const toggleErrorTag = (questionId: string, tag: string) => {
    setErrorTagsMap((prev) => {
      const current = prev[questionId] || []
      const next = current.includes(tag) ? current.filter((x) => x !== tag) : [...current, tag]
      return { ...prev, [questionId]: next }
    })
  }

  const toggleAnswerVisible = (questionId: string) => {
    setAnswerVisibleMap((prev) => ({
      ...prev,
      [questionId]: !prev[questionId],
    }))
  }

  const submitResult = (questionId: string, result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED') => {
    const selectedTags = errorTagsMap[questionId] || []
    if ((result === 'WRONG' || result === 'PARTIAL') && selectedTags.length === 0) {
      toast({
        title: '请先选择错因',
        description: '半对和错误都必须至少选择一个错因标签',
        variant: 'destructive',
      })
      return
    }
    completeMutation.mutate({
      questionId,
      result,
      errorTags: selectedTags,
    })
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">今日复习</h1>
          <p className="text-sm text-muted-foreground">优先复习到期较早、熟练度较低的题目{data?.date ? ` · ${data.date}` : ''}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">待复习 {total} 题</Badge>
          <Button variant="outline" onClick={() => setShowFullQuestion((prev) => !prev)}>
            {showFullQuestion ? '隐藏完整题干与选项' : '显示完整题干与选项'}
          </Button>
          <Button
            onClick={() => generateDailySetMutation.mutate()}
            disabled={generateDailySetMutation.isPending || total === 0 || isError}
          >
            {generateDailySetMutation.isPending ? '生成中...' : '生成待复习组卷并下载'}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={subject || '__all__'} onValueChange={(value) => {
          setSubject(value === '__all__' ? undefined : value)
          setPage(1)
        }}>
          <SelectTrigger className="w-48" aria-label="筛选学科"><SelectValue placeholder="全部学科" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部学科</SelectItem>
            {subjects.map((name) => <SelectItem key={name} value={name}>{name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={String(pageSize)} onValueChange={(value) => { setPageSize(Number(value)); setPage(1) }}>
          <SelectTrigger className="w-36" aria-label="每页题数"><SelectValue /></SelectTrigger>
          <SelectContent>
            {[20, 50, 100].map((size) => <SelectItem key={size} value={String(size)}>每页 {size} 题</SelectItem>)}
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">组卷包含当前学科下的全部待复习题目，不受分页影响。</span>
      </div>

      {isError ? (
        <Card><CardContent className="flex items-center gap-3 py-8 text-sm">
          <span>复习队列加载失败，请重试。</span>
          <Button variant="outline" size="sm" onClick={() => refetch()}>重新加载</Button>
        </CardContent></Card>
      ) : isLoading ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">加载中...</CardContent>
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">{subject ? '当前学科暂无待复习题目，可切换其他学科。' : '今日暂无待复习题目'}</CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const question = item.question
            const answer = item.answer
            const options = normalizeOptions(question?.content_json)
            const answerImages = Array.isArray(answer?.images) ? answer.images : []
            const answerText = answer?.answer_latex || answer?.answer_text
            const explanation = answer?.explanation_latex || answer?.explanation_text

            return (
            <Card key={item.progress_id}>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">题目 {item.question_id.slice(0, 8)}...</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                  <Badge variant="outline">优先级 {item.priority}</Badge>
                  <Badge variant="outline">熟练度 {item.proficiency_score}</Badge>
                  <Badge variant="outline">阶段 {item.review_stage}</Badge>
                  <Badge variant="outline">{REVIEW_REASONS[item.reason] || item.reason}</Badge>
                  {question?.subject && <Badge variant="outline">{question.subject}</Badge>}
                  {item.next_review_at && <span>计划复习：{new Date(item.next_review_at).toLocaleString()}</span>}
                </div>

                {showFullQuestion && (
                  <div className="space-y-3 rounded-md border bg-muted/20 p-3">
                      <>
                        <LatexContent
                          text={
                            question?.stem_latex ||
                            question?.stem_text ||
                            question?.content_text ||
                            question?.content ||
                            '（暂无题干）'
                          }
                          className="prose prose-sm max-w-none whitespace-pre-wrap text-sm"
                        />
                        {question?.appendix && <LatexContent text={question.appendix} className="whitespace-pre-wrap text-sm text-muted-foreground" />}
                        {question?.stem_images?.map((image, index) => image.url && (
                          <img key={image.image_id} src={image.url} alt={`题干图片 ${index + 1}`} className="h-auto max-w-full rounded-lg border" />
                        ))}
                        {options.length > 0 && (
                          <div className="space-y-2 rounded-md border bg-background p-3">
                            {options.map((option) => (
                              <div key={option.key} className="flex gap-2 text-sm">
                                <span className="font-medium">{option.key}.</span>
                                <LatexContent text={option.text} className="whitespace-pre-wrap" />
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleAnswerVisible(item.question_id)}
                    >
                      {answerVisibleMap[item.question_id] ? '隐藏答案' : '显示答案'}
                    </Button>
                    {answerVisibleMap[item.question_id] && (
                      <div className="rounded-md border bg-background p-3">
                        {answerText && (
                          <LatexContent
                            text={answerText}
                            className="whitespace-pre-wrap text-sm"
                          />
                        )}
                        {explanation && <div className="mt-3 space-y-1">
                          <p className="text-sm font-medium">解析</p>
                          <LatexContent text={explanation} className="whitespace-pre-wrap text-sm" />
                        </div>}
                        {answerImages.length > 0 && (
                            <div className="mt-3 space-y-3">
                              {answerImages.map((image, index) => (
                                <img
                                  key={image.image_id || index}
                                  src={image.url}
                                  alt={`答案图片 ${index + 1}`}
                                  className="h-auto max-w-full rounded-lg border"
                                />
                              ))}
                            </div>
                          )}
                        {!answerText && !explanation && answerImages.length === 0 && (
                            <span className="text-sm text-muted-foreground">暂无答案</span>
                          )}
                      </div>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 rounded-md border p-3 md:grid-cols-4">
                  {ERROR_TAGS.map((tag) => (
                    <label key={`${item.question_id}-${tag.code}`} className="flex items-center gap-2 text-xs">
                      <Checkbox
                        checked={(errorTagsMap[item.question_id] || []).includes(tag.code)}
                        onCheckedChange={() => toggleErrorTag(item.question_id, tag.code)}
                      />
                      <span>{tag.name}</span>
                    </label>
                  ))}
                </div>

                <div className="flex flex-wrap gap-2">
                  <Link href={`/dashboard/questions/${item.question_id}`}>
                    <Button variant="outline" size="sm">去做题</Button>
                  </Link>
                  <Button
                    size="sm"
                    className="bg-green-600 hover:bg-green-700"
                    disabled={completeMutation.isPending}
                    onClick={() => submitResult(item.question_id, 'CORRECT')}
                  >
                    标记正确
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-amber-600 text-amber-700 hover:bg-amber-50"
                    disabled={completeMutation.isPending}
                    onClick={() => submitResult(item.question_id, 'PARTIAL')}
                  >
                    标记半对（需错因）
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-red-600 text-red-600 hover:bg-red-50"
                    disabled={completeMutation.isPending}
                    onClick={() => submitResult(item.question_id, 'WRONG')}
                  >
                    标记错误（含错因）
                  </Button>
                </div>
              </CardContent>
            </Card>
            )
          })}
        </div>
      )}
      {!isError && total > 0 && (
        <div className="flex items-center justify-between gap-3 text-sm">
          <span className="text-muted-foreground">共 {total} 题 · 第 {page} / {Math.max(1, data?.total_pages || 0)} 页</span>
          <div className="flex gap-2">
            <Button variant="outline" disabled={isLoading || page <= 1} onClick={() => setPage((value) => value - 1)}>上一页</Button>
            <Button variant="outline" disabled={isLoading || page >= (data?.total_pages || 0)} onClick={() => setPage((value) => value + 1)}>下一页</Button>
          </div>
        </div>
      )}
    </div>
  )
}
