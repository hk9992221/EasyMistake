'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { answersApi, exportsApi, paperSetsApi, questionsApi, reviewsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
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

  const { data, isLoading } = useQuery({
    queryKey: ['reviews-today-page'],
    queryFn: () => reviewsApi.getToday(),
  })

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
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['reviews-today-page'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-reviews-today'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-analytics-overview'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-error-tags'] })
      setErrorTagsMap((prev) => ({ ...prev, [variables.questionId]: [] }))
    },
    onError: () => {
      toast({ title: '提交失败', description: '请稍后重试', variant: 'destructive' })
    },
  })

  const generateDailySetMutation = useMutation({
    mutationFn: async () => {
      const items = data?.items || []
      if (items.length === 0) {
        throw new Error('今日无待复习题目')
      }

      const now = new Date()
      const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
      const dailyTitle = `复习-${dateStr}`
      const existingSets = await paperSetsApi.list({ page: 1, page_size: 50, search: dailyTitle })
      const reusableSet = (existingSets.items || []).find((x: any) => x.title === dailyTitle)

      const paperSet = reusableSet
        ? reusableSet
        : await paperSetsApi.create({
            title: dailyTitle,
            subject: '复习',
            description: `每日复习自动组卷（${dateStr}）`,
            output_format: 'LATEX',
          } as any)

      // 同步为“当天复习队列”，复用时先清空旧题目再重建，保证内容一致
      const existingItems = await paperSetsApi.getItems(paperSet.id).catch(() => [])
      await Promise.all(
        (existingItems || []).map((it: any) => paperSetsApi.removeItem(paperSet.id, it.question_id || it.questionId)),
      )
      await paperSetsApi.batchAddItems(
        paperSet.id,
        items.map((item, index) => ({
          question_id: item.question_id,
          order_index: index + 1,
        })),
      )

      const exportTask = await exportsApi.create({
        paper_set_id: paperSet.id,
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
        throw new Error('导出超时，请到组卷管理查看')
      }

      const blob = await exportsApi.download(current.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `复习-${dateStr}.zip`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      return current
    },
    onSuccess: () => {
      toast({ title: '已复用/生成并下载', description: '今日复习组卷 LaTeX 导出完成' })
    },
    onError: (error: any) => {
      toast({ title: '生成失败', description: error?.message || '请稍后重试', variant: 'destructive' })
    },
  })

  const items = data?.items || []
  const questionIds = items.map((item) => item.question_id)

  const { data: questionDetailsMap = {}, isFetching: isFetchingQuestionDetails } = useQuery({
    queryKey: ['reviews-today-question-details', questionIds.join(',')],
    enabled: showFullQuestion && questionIds.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        questionIds.map(async (id) => {
          const [question, answer] = await Promise.all([
            questionsApi.get(id).catch(() => null),
            answersApi.getByQuestionId(id).catch(() => null),
          ])
          return [id, { question, answer }] as const
        }),
      )
      return Object.fromEntries(entries)
    },
  })

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
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">今日复习</h1>
          <p className="text-sm text-muted-foreground">按优先级安排今天的复习题目</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">待复习 {items.length} 题</Badge>
          <Button variant="outline" onClick={() => setShowFullQuestion((prev) => !prev)}>
            {showFullQuestion ? '隐藏完整题干与选项' : '显示完整题干与选项'}
          </Button>
          <Button
            onClick={() => generateDailySetMutation.mutate()}
            disabled={generateDailySetMutation.isPending || items.length === 0}
          >
            {generateDailySetMutation.isPending ? '生成中...' : '生成今日LaTeX组卷并下载'}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">加载中...</CardContent>
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">今日暂无待复习题目</CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const detail = questionDetailsMap[item.question_id]
            const question = detail?.question
            const answer = detail?.answer
            const options = normalizeOptions(question?.content_json)
            const answerImages = Array.isArray(answer?.images) ? answer.images : []

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
                  <Badge variant="outline">{item.reason}</Badge>
                </div>

                {showFullQuestion && (
                  <div className="space-y-3 rounded-md border bg-muted/20 p-3">
                    {isFetchingQuestionDetails && !detail ? (
                      <div className="text-sm text-muted-foreground">题目加载中...</div>
                    ) : (
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
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleAnswerVisible(item.question_id)}
                      disabled={isFetchingQuestionDetails && !detail}
                    >
                      {answerVisibleMap[item.question_id] ? '隐藏答案' : '显示答案'}
                    </Button>
                    {answerVisibleMap[item.question_id] && (
                      <div className="rounded-md border bg-background p-3">
                        {answer?.answer_text && (
                          <LatexContent
                            text={answer.answer_text}
                            className="whitespace-pre-wrap text-sm"
                          />
                        )}
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
                        {!answer?.answer_text && answerImages.length === 0 && (
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
    </div>
  )
}
