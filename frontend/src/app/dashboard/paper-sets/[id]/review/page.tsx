'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { answersApi, attemptsApi, paperSetsApi, questionProgressApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import { LatexContent } from '@/components/latex-content'
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  CircleSlash,
  XCircle,
} from 'lucide-react'
import { useToast } from '@/lib/hooks/use-toast'

type OptionItem = {
  key: string
  text: string
}

function parseMaybeJson(input: unknown): any {
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
  const raw = (data as any).options ?? (data as any).choices
  if (!Array.isArray(raw)) return []

  return raw
    .map((item: any, index: number) => {
      if (!item || typeof item !== 'object') return null
      const key = String(item.key ?? item.label ?? String.fromCharCode(65 + index)).trim()
      const text = String(item.text ?? item.content ?? '').trim()
      if (!text) return null
      return { key, text }
    })
    .filter((item: OptionItem | null): item is OptionItem => Boolean(item))
}

function calcMastery(attempts: any[] = []) {
  const correct = attempts.filter((a) => a.result === 'CORRECT').length
  const wrong = attempts.filter((a) => a.result === 'WRONG').length
  const skipped = attempts.filter((a) => a.result === 'SKIPPED').length
  const effective = correct + wrong
  const mastery = effective > 0 ? Math.round((correct / effective) * 100) : 0
  return { correct, wrong, skipped, effective, mastery }
}

const REVIEW_RETURN_CONTEXT_KEY = 'paper_set_review_return_context'
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
const ERROR_TAG_LABELS = Object.fromEntries(ERROR_TAGS.map((item) => [item.code, item.name])) as Record<string, string>

export default function PaperSetReviewPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const paperSetId = params.id as string
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const [currentIndex, setCurrentIndex] = useState(0)
  const [showAnswer, setShowAnswer] = useState(true)
  const [note, setNote] = useState('')
  const [errorTagsMap, setErrorTagsMap] = useState<Record<string, string[]>>({})

  const { data: previewData, isLoading } = useQuery({
    queryKey: ['paper-set-preview', paperSetId],
    queryFn: () => paperSetsApi.preview(paperSetId),
    enabled: !!paperSetId,
  })

  const questions = previewData?.questions || []
  const currentQuestion = questions[currentIndex]
  const questionIds = useMemo(() => questions.map((q: any) => q.id), [questions])

  useEffect(() => {
    if (questions.length === 0) return
    const rawIndex = searchParams.get('index')
    if (!rawIndex) return
    const parsed = Number.parseInt(rawIndex, 10)
    if (Number.isNaN(parsed)) return
    const clamped = Math.min(Math.max(parsed, 0), questions.length - 1)
    setCurrentIndex(clamped)
  }, [questions.length, searchParams])

  const { data: attemptsMap = {}, isFetching: isFetchingAttempts } = useQuery({
    queryKey: ['paper-set-review-attempts', paperSetId, questionIds.join(',')],
    enabled: questionIds.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        questionIds.map(async (id: string) => {
          const attempts = await attemptsApi.getByQuestionId(id)
          return [id, attempts] as const
        }),
      )
      return Object.fromEntries(entries)
    },
  })

  const { data: progressMap = {}, isFetching: isFetchingProgress } = useQuery({
    queryKey: ['paper-set-review-progress', paperSetId, questionIds.join(',')],
    enabled: questionIds.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        questionIds.map(async (id: string) => {
          const progressResp = await questionProgressApi.list({ page: 1, pageSize: 1, questionId: id })
          return [id, progressResp.items?.[0] || null] as const
        }),
      )
      return Object.fromEntries(entries)
    },
  })

  const { data: currentAnswer } = useQuery({
    queryKey: ['paper-set-review-answer', currentQuestion?.id],
    enabled: !!currentQuestion?.id && showAnswer,
    queryFn: async () => {
      try {
        return await answersApi.getByQuestionId(currentQuestion.id)
      } catch {
        return null
      }
    },
  })

  const createAttemptMutation = useMutation({
    mutationFn: (payload: { question_id: string; result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED'; wrong_reason?: string; note?: string; error_tags?: string[]; source?: string; review_mode?: string }) =>
      attemptsApi.create(payload as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-set-review-attempts', paperSetId] })
      queryClient.invalidateQueries({ queryKey: ['paper-set-review-progress', paperSetId] })
      queryClient.invalidateQueries({ queryKey: ['attempts'] })
      setNote('')
      setErrorTagsMap((prev) => ({ ...prev, [currentQuestion.id]: [] }))
      if (currentIndex < questions.length - 1) {
        setCurrentIndex((v) => v + 1)
        setShowAnswer(true)
      }
    },
    onError: () => {
      toast({ title: '记录失败', description: '请稍后重试。', variant: 'destructive' })
    },
  })

  const totalStats = useMemo(() => {
    const allAttempts = Object.values(attemptsMap).flat() as any[]
    const correct = allAttempts.filter((a) => a.result === 'CORRECT').length
    const wrong = allAttempts.filter((a) => a.result === 'WRONG').length
    const skipped = allAttempts.filter((a) => a.result === 'SKIPPED').length
    const progressList = Object.values(progressMap).filter(Boolean) as any[]
    const mastery = progressList.length
      ? Math.round(progressList.reduce((acc: number, item: any) => acc + Number(item.proficiency_score || 0), 0) / progressList.length)
      : 0
    const masteredCount = questions.filter((q: any) => {
      const progress = (progressMap as any)[q.id]
      return progress && Number(progress.proficiency_score || 0) >= 80
    }).length

    return {
      totalAttempts: allAttempts.length,
      correct,
      wrong,
      skipped,
      mastery,
      masteredCount,
    }
  }, [attemptsMap, progressMap, questions])

  if (isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">加载中...</div>
  }

  if (!previewData || questions.length === 0) {
    return (
      <div className="p-8">
        <p className="text-sm text-muted-foreground">当前组卷没有题目。</p>
        <Link href="/dashboard/paper-sets">
          <Button className="mt-4" variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />返回组卷
          </Button>
        </Link>
      </div>
    )
  }

  const options = normalizeOptions(currentQuestion?.content_json)
  const type = String(currentQuestion?.type || '').toUpperCase()
  const isChoice = type === 'MCQ' || type === 'SINGLE_CHOICE' || type === 'MULTIPLE_CHOICE' || options.length > 0

  const currentAttempts = ((attemptsMap as any)[currentQuestion.id] || []) as any[]
  const currentStats = calcMastery(currentAttempts)
  const currentProgress = (progressMap as any)[currentQuestion.id]
  const currentMastery = currentProgress ? Number(currentProgress.proficiency_score || 0) : currentStats.mastery
  const selectedTags = errorTagsMap[currentQuestion.id] || []
  const currentErrorTagStats = currentAttempts
    .filter((item: any) => item.result === 'WRONG' || item.result === 'PARTIAL')
    .reduce((acc: Record<string, number>, item: any) => {
      const tags: string[] = Array.isArray(item.error_tags) ? item.error_tags : []
      tags.forEach((tag) => {
        acc[tag] = (acc[tag] || 0) + 1
      })
      return acc
    }, {})
  const currentErrorTagList = Object.entries(currentErrorTagStats)
    .map(([tag, count]) => ({
      tag,
      name: ERROR_TAG_LABELS[tag] || tag,
      count,
    }))
    .sort((a, b) => b.count - a.count)

  const toggleErrorTag = (questionId: string, tag: string) => {
    setErrorTagsMap((prev) => {
      const current = prev[questionId] || []
      const next = current.includes(tag) ? current.filter((x) => x !== tag) : [...current, tag]
      return { ...prev, [questionId]: next }
    })
  }

  const submitResult = (result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED') => {
    if ((result === 'WRONG' || result === 'PARTIAL') && selectedTags.length === 0) {
      toast({
        title: '请先选择错因',
        description: '半对和错误都必须至少选择一个错因标签',
        variant: 'destructive',
      })
      return
    }

    createAttemptMutation.mutate({
      question_id: currentQuestion.id,
      result,
      source: 'paper_set_review',
      review_mode: `paper_set:${paperSetId}`,
      note: note || undefined,
      error_tags: selectedTags,
    })
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Link href={`/dashboard/paper-sets/${paperSetId}`}>
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />返回组卷
            </Button>
          </Link>
          <Button
            variant="outline"
            onClick={() => {
              setCurrentIndex((v) => Math.max(0, v - 1))
              setShowAnswer(true)
            }}
            disabled={currentIndex <= 0}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />上一题
          </Button>
          <Button
            onClick={() => {
              setCurrentIndex((v) => Math.min(questions.length - 1, v + 1))
              setShowAnswer(true)
            }}
            disabled={currentIndex >= questions.length - 1}
          >
            下一题<ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
        <div className="text-sm text-muted-foreground">
          第 {currentIndex + 1} / {questions.length} 题
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-5">
        <Card className="md:col-span-3">
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{currentQuestion.type || 'UNKNOWN'}</Badge>
              {typeof currentQuestion.score === 'number' && <Badge variant="secondary">{currentQuestion.score} 分</Badge>}
              {currentQuestion.section_title && <Badge variant="secondary">{currentQuestion.section_title}</Badge>}
              {currentQuestion.subject && <Badge variant="outline">{currentQuestion.subject}</Badge>}
            </div>
            <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
              <div>
                来源：{currentQuestion.book_name || '-'}
                {currentQuestion.chapter_name ? ` / ${currentQuestion.chapter_name}` : ''}
              </div>
              <div>页码：{currentQuestion.page_no ?? '-'}</div>
              <div>题号：{currentQuestion.question_no || '-'}</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <LatexContent
              text={currentQuestion.stem_latex || currentQuestion.stem_text || ''}
              className="prose prose-sm max-w-none whitespace-pre-wrap"
            />

            {isChoice && options.length > 0 && (
              <div className="space-y-2 rounded-md border bg-muted/20 p-4">
                {options.map((opt) => (
                  <div key={opt.key} className="flex gap-2 text-sm">
                    <span className="font-medium">{opt.key}.</span>
                    <LatexContent text={opt.text} className="whitespace-pre-wrap" />
                  </div>
                ))}
              </div>
            )}

            {currentQuestion?.appendix && (
              <div className="rounded-md border bg-muted/20 p-4 text-sm">
                <div className="mb-2 font-medium">备注/附录</div>
                <LatexContent text={currentQuestion.appendix} className="whitespace-pre-wrap" />
              </div>
            )}

            {showAnswer && (
              <div className="rounded-md border bg-muted/20 p-4 text-sm">
                <div className="mb-2 font-medium">答案</div>
                {currentAnswer?.answer_text && (
                  <LatexContent text={currentAnswer.answer_text} className="whitespace-pre-wrap" />
                )}
                {Array.isArray((currentAnswer as any)?.images) && (currentAnswer as any).images.length > 0 && (
                  <div className="mt-3 space-y-3">
                    {(currentAnswer as any).images.map((image: any, index: number) => (
                      <img
                        key={image.image_id || index}
                        src={image.url}
                        alt={`答案图片 ${index + 1}`}
                        className="max-w-full h-auto rounded-lg border"
                      />
                    ))}
                  </div>
                )}
                {!currentAnswer?.answer_text &&
                  (!Array.isArray((currentAnswer as any)?.images) || (currentAnswer as any).images.length === 0) && (
                    <span className="text-muted-foreground">暂无答案</span>
                  )}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-3 md:col-span-2">
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => {
              const context = {
                source: 'paper-set-review',
                paperSetId,
                questionId: currentQuestion.id,
                reviewIndex: currentIndex,
              }
              sessionStorage.setItem(REVIEW_RETURN_CONTEXT_KEY, JSON.stringify(context))
              router.push(
                `/dashboard/questions/${currentQuestion.id}?from_review=1&paper_set_id=${paperSetId}&review_index=${currentIndex}`
              )
            }}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            跳到问题
          </Button>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">批改与掌握度</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>本题正确: {currentStats.correct}</div>
                <div>本题错误: {currentStats.wrong}</div>
                <div>本题跳过: {currentStats.skipped}</div>
                <div>本题掌握: {currentMastery}%</div>
              </div>

              {currentErrorTagList.length > 0 && (
                <div className="rounded-md border p-3">
                  <div className="mb-2 text-sm font-medium">历史错因统计（本题）</div>
                  <div className="flex flex-wrap gap-2">
                    {currentErrorTagList.map((item) => (
                      <Badge key={item.tag} variant="outline">
                        {item.name} x {item.count}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <Textarea
                placeholder="备注（可选）"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="min-h-[72px]"
              />
              <div className="grid grid-cols-2 gap-2 rounded-md border p-3 md:grid-cols-4">
                {ERROR_TAGS.map((tag) => (
                  <label key={`${currentQuestion.id}-${tag.code}`} className="flex items-center gap-2 text-xs">
                    <Checkbox
                      checked={selectedTags.includes(tag.code)}
                      onCheckedChange={() => toggleErrorTag(currentQuestion.id, tag.code)}
                    />
                    <span>{tag.name}</span>
                  </label>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-2">
                <Button
                  className="bg-green-600 hover:bg-green-700"
                  onClick={() => submitResult('CORRECT')}
                  disabled={createAttemptMutation.isPending}
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" />掌握（正确）
                </Button>
                <Button
                  variant="outline"
                  className="border-amber-600 text-amber-700 hover:bg-amber-50 hover:text-amber-800"
                  onClick={() => submitResult('PARTIAL')}
                  disabled={createAttemptMutation.isPending}
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" />半对（需错因）
                </Button>

                <Button
                  variant="outline"
                  className="border-red-600 text-red-600 hover:bg-red-50 hover:text-red-700"
                  onClick={() => submitResult('WRONG')}
                  disabled={createAttemptMutation.isPending}
                >
                  <XCircle className="mr-2 h-4 w-4" />未掌握（错误，需错因）
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => submitResult('SKIPPED')}
                  disabled={createAttemptMutation.isPending}
                >
                  <CircleSlash className="mr-2 h-4 w-4" />跳过
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">组卷总体掌握统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-6">
            <div>题目数: {questions.length}</div>
            <div>记录数: {totalStats.totalAttempts}</div>
            <div>正确: {totalStats.correct}</div>
            <div>错误: {totalStats.wrong}</div>
            <div>跳过: {totalStats.skipped}</div>
            <div>总体掌握: {totalStats.mastery}%</div>
          </div>
          <div className="mt-2 text-sm text-muted-foreground">
            已掌握题目: {totalStats.masteredCount}/{questions.length}
            {isFetchingAttempts || isFetchingProgress ? '（统计刷新中）' : ''}
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <div />
      </div>
    </div>
  )
}
