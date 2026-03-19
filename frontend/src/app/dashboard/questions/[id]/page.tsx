'use client'

// Force dynamic rendering for this route
export const dynamic = 'force-dynamic'

import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { answersApi, attemptsApi, paperSetsApi, questionsApi, imagesApi, questionProgressApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/lib/api/client'
import { ArrowLeft, Check, Copy, Eye, EyeOff, Edit, Save, X, Trash2, Upload, Plus } from 'lucide-react'
import { useToast } from '@/lib/hooks/use-toast'
import { LatexContent } from '@/components/latex-content'
import { getQuestionTypeLabel } from '@/lib/question-type'
import { parseLabels } from '@/lib/label-parser'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

type McqOption = {
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

function normalizeOptions(contentJson: unknown): McqOption[] {
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
    .filter((item: McqOption | null): item is McqOption => Boolean(item))
}

const REVIEW_RETURN_CONTEXT_KEY = 'paper_set_review_return_context'
const PAPER_SET_DETAIL_RETURN_CONTEXT_KEY = 'paper_set_detail_return_context'
const ERROR_TAG_LABELS: Record<string, string> = {
  KNOWLEDGE: '知识点不会',
  CONCEPT: '概念不清',
  METHOD: '方法不会',
  STRATEGY: '思路卡住',
  CALCULATION: '计算错误',
  CARELESS: '粗心',
  MISREAD: '审题错误',
  TIME_PRESSURE: '时间不够',
}

function extractPaperSetId(reviewMode?: string | null): string | null {
  if (!reviewMode || !reviewMode.startsWith('paper_set:')) return null
  const paperSetId = reviewMode.slice('paper_set:'.length).trim()
  return paperSetId || null
}

export default function QuestionDetailPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const questionId = params.id as string
  const contextPaperSetId = searchParams.get('paper_set_id')
  const fromPaperSetReview = searchParams.get('from_review') === '1' && !!contextPaperSetId
  const fromPaperSetDetail = searchParams.get('from_paper_set') === '1' && !!contextPaperSetId
  const [reviewReturnUrl, setReviewReturnUrl] = useState<string | null>(null)
  const [paperSetReturnUrl, setPaperSetReturnUrl] = useState<string | null>(null)

  const [showAnswer, setShowAnswer] = useState(false)
  const [showAppendix, setShowAppendix] = useState(false)
  const [isEditingAppendix, setIsEditingAppendix] = useState(false)
  const [isEditingStem, setIsEditingStem] = useState(false)
  const [isEditingAnswer, setIsEditingAnswer] = useState(false)
  const [isEditingMetadata, setIsEditingMetadata] = useState(false)
  const [appendixContent, setAppendixContent] = useState('')
  const [stemContent, setStemContent] = useState('')
  const [answerContent, setAnswerContent] = useState('')
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)
  const [isUploadingStemImage, setIsUploadingStemImage] = useState(false)
  const [isUploadingAnswerImage, setIsUploadingAnswerImage] = useState(false)
  const [copiedPrompt, setCopiedPrompt] = useState(false)
  const [optionEditor, setOptionEditor] = useState<McqOption[]>([])
  const stemImageInputRef = useRef<HTMLInputElement>(null)
  const answerImageInputRef = useRef<HTMLInputElement>(null)

  // 元数据编辑状态
  const [metadata, setMetadata] = useState({
    subject: '',
    type: '',
    difficulty: '',
    book_name: '',
    chapter_name: '',
    page_no: '',
    question_no: '',
    tags_text: '',
    knowledge_points_text: '',
  })

  useEffect(() => {
    const fromReview = searchParams.get('from_review')
    const paperSetId = searchParams.get('paper_set_id')
    const reviewIndexRaw = searchParams.get('review_index')
    if (fromReview !== '1' || !paperSetId || !reviewIndexRaw) {
      setReviewReturnUrl(null)
      return
    }

    const reviewIndex = Number.parseInt(reviewIndexRaw, 10)
    if (Number.isNaN(reviewIndex) || reviewIndex < 0) {
      setReviewReturnUrl(null)
      return
    }

    const rawContext = sessionStorage.getItem(REVIEW_RETURN_CONTEXT_KEY)
    if (!rawContext) {
      setReviewReturnUrl(null)
      return
    }

    try {
      const context = JSON.parse(rawContext)
      const isValidContext =
        context?.source === 'paper-set-review' &&
        context?.paperSetId === paperSetId &&
        context?.questionId === questionId &&
        Number(context?.reviewIndex) === reviewIndex

      if (!isValidContext) {
        setReviewReturnUrl(null)
        return
      }

      setReviewReturnUrl(`/dashboard/paper-sets/${paperSetId}/review?index=${reviewIndex}`)
    } catch {
      setReviewReturnUrl(null)
    }
  }, [questionId, searchParams])

  useEffect(() => {
    const fromPaperSet = searchParams.get('from_paper_set')
    const paperSetId = searchParams.get('paper_set_id')
    const questionIndexRaw = searchParams.get('question_index')
    if (fromPaperSet !== '1' || !paperSetId || !questionIndexRaw) {
      setPaperSetReturnUrl(null)
      return
    }

    const questionIndex = Number.parseInt(questionIndexRaw, 10)
    if (Number.isNaN(questionIndex) || questionIndex < 0) {
      setPaperSetReturnUrl(null)
      return
    }

    const rawContext = sessionStorage.getItem(PAPER_SET_DETAIL_RETURN_CONTEXT_KEY)
    if (!rawContext) {
      setPaperSetReturnUrl(null)
      return
    }

    try {
      const context = JSON.parse(rawContext)
      const isValidContext =
        context?.source === 'paper-set-detail' &&
        context?.paperSetId === paperSetId &&
        context?.questionId === questionId &&
        Number(context?.questionIndex) === questionIndex

      if (!isValidContext) {
        setPaperSetReturnUrl(null)
        return
      }

      setPaperSetReturnUrl(`/dashboard/paper-sets/${paperSetId}`)
    } catch {
      setPaperSetReturnUrl(null)
    }
  }, [questionId, searchParams])

  const { data: question, isLoading } = useQuery({
    queryKey: ['question', questionId],
    queryFn: () => questionsApi.get(questionId),
    enabled: !!questionId,
  })

  const { data: answer } = useQuery<any | null>({
    queryKey: ['answer', questionId],
    queryFn: async () => {
      try {
        const response = await apiClient.get<any>(`/questions/${questionId}/answer`)
        return response.data
      } catch (error) {
        return null
      }
    },
    enabled: !!questionId,
    retry: false,
  })

  const { data: attempts } = useQuery({
    queryKey: ['attempts', questionId],
    queryFn: () => attemptsApi.getByQuestionId(questionId),
    enabled: !!questionId,
  })

  const wrongPaperSetIds = Array.from(
    new Set(
      (attempts || [])
        .filter((item: any) => item.result === 'WRONG')
        .map((item: any) => extractPaperSetId(item.review_mode))
        .filter((id): id is string => Boolean(id)),
    ),
  )

  const { data: wrongPaperSetMap = {} } = useQuery({
    queryKey: ['wrong-paper-sets-by-question', questionId, wrongPaperSetIds.join(',')],
    enabled: wrongPaperSetIds.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        wrongPaperSetIds.map(async (paperSetId) => {
          try {
            const paperSet = await paperSetsApi.get(paperSetId)
            return [paperSetId, paperSet] as const
          } catch {
            return [paperSetId, null] as const
          }
        }),
      )
      return Object.fromEntries(entries)
    },
  })

  const { data: progressData } = useQuery({
    queryKey: ['question-progress', questionId],
    queryFn: () => questionProgressApi.list({ page: 1, pageSize: 1, questionId }),
    enabled: !!questionId,
  })

  const updateStemMutation = useMutation({
    mutationFn: ({ stemText, options }: { stemText: string; options: McqOption[] }) => {
      const currentContentJson = parseMaybeJson(question?.content_json) || {}
      const filteredOptions = options
        .map((item) => ({ key: item.key.trim(), text: item.text.trim() }))
        .filter((item) => item.key && item.text)
      const nextContentJson = { ...currentContentJson }
      if (filteredOptions.length > 0) {
        ;(nextContentJson as any).options = filteredOptions
      } else {
        delete (nextContentJson as any).options
      }
      return questionsApi.update(questionId, {
        stem_text: stemText.trim() ? stemText : null,
        content_json: nextContentJson,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['question', questionId] })
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      setIsEditingStem(false)
      toast({
        title: 'Saved',
        description: 'Question stem updated.',
      })
    },
    onError: () => {
      toast({
        title: 'Save failed',
        description: 'Unable to update question stem.',
        variant: 'destructive',
      })
    },
  })

  const updateAnswerMutation = useMutation({
    mutationFn: (answerText: string) =>
      answersApi.update(questionId, {
        answer_text: answerText.trim() ? answerText : null,
        answer_type:
          (answerText.trim() ? 'TEXT' : 'NONE') as 'TEXT' | 'NONE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['answer', questionId] })
      setIsEditingAnswer(false)
      toast({
        title: 'Saved',
        description: 'Answer updated.',
      })
    },
    onError: () => {
      toast({
        title: 'Save failed',
        description: 'Unable to update answer.',
        variant: 'destructive',
      })
    },
  })

  const updateAppendixMutation = useMutation({
    mutationFn: (appendix: string) =>
      questionsApi.update(questionId, { appendix: appendix.trim() || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['question', questionId] })
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      setIsEditingAppendix(false)
      toast({
        title: '已保存',
        description: '附录已更新',
      })
    },
    onError: () => {
      toast({
        title: '保存失败',
        description: '无法更新附录',
        variant: 'destructive',
      })
    },
  })

  const updateMetadataMutation = useMutation({
    mutationFn: (data: typeof metadata) =>
      questionsApi.update(questionId, {
        subject: data.subject || null,
        type: data.type || undefined,
        difficulty: data.difficulty || null,
        book_name: data.book_name || null,
        chapter_name: data.chapter_name || null,
        page_no: data.page_no ? parseInt(data.page_no) : null,
        question_no: data.question_no || null,
        tags_json: parseLabels(data.tags_text),
        knowledge_points_json: parseLabels(data.knowledge_points_text),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['question', questionId] })
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      setIsEditingMetadata(false)
      toast({
        title: '已保存',
        description: '题目信息已更新',
      })
    },
    onError: () => {
      toast({
        title: '保存失败',
        description: '无法更新题目信息',
        variant: 'destructive',
      })
    },
  })

  const createAttemptMutation = useMutation({
    mutationFn: (result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED') =>
      attemptsApi.create({
        question_id: questionId,
        result,
        source: fromPaperSetReview || fromPaperSetDetail ? 'paper_set_review' : 'practice',
        review_mode:
          (fromPaperSetReview || fromPaperSetDetail) && contextPaperSetId
            ? `paper_set:${contextPaperSetId}`
            : undefined,
      } as any),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attempts', questionId] })
      queryClient.invalidateQueries({ queryKey: ['question-progress', questionId] })
      toast({
        title: 'Recorded',
        description: 'Attempt saved.',
      })
    },
    onError: () => {
      toast({
        title: 'Save failed',
        description: 'Unable to record attempt.',
        variant: 'destructive',
      })
    },
  })

  const deleteQuestionMutation = useMutation({
    mutationFn: () => questionsApi.delete(questionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      toast({
        title: '已删除',
        description: '试题已成功删除',
      })
      setShowDeleteDialog(false)
      router.push('/dashboard/questions')
    },
    onError: () => {
      toast({
        title: '删除失败',
        description: '无法删除试题',
        variant: 'destructive',
      })
    },
  })

  const handleSaveAppendix = () => {
    updateAppendixMutation.mutate(appendixContent)
  }

  const handleStartEditStem = () => {
    setStemContent(question?.stem_text || question?.content_text || question?.content || '')
    setOptionEditor(normalizeOptions(question?.content_json))
    setIsEditingStem(true)
  }

  const handleSaveStem = () => {
    updateStemMutation.mutate({ stemText: stemContent, options: optionEditor })
  }

  const handleStartEditAnswer = () => {
    setAnswerContent(answer?.answer_text || '')
    setIsEditingAnswer(true)
    setShowAnswer(true)
  }

  const handleSaveAnswer = () => {
    updateAnswerMutation.mutate(answerContent)
  }

  const resolveAnswerType = (answerText: string, imageCount: number) => {
    const hasText = answerText.trim().length > 0
    const hasImages = imageCount > 0
    if (hasText && hasImages) return 'MIXED' as const
    if (hasText) return 'TEXT' as const
    if (hasImages) return 'IMAGE' as const
    return 'NONE' as const
  }

  const upsertAnswerImages = async (nextImages: Array<{ image_id: string; order_index: number }>) => {
    const text = isEditingAnswer ? answerContent : answer?.answer_text || ''
    await answersApi.upsert(questionId, {
      answer_text: text.trim() ? text : null,
      answer_type: resolveAnswerType(text, nextImages.length),
      images: nextImages,
    })
    await queryClient.invalidateQueries({ queryKey: ['answer', questionId] })
  }

  const handleUploadAnswerImages = async (files: File[]) => {
    if (files.length === 0) return
    setIsUploadingAnswerImage(true)
    try {
      const existingImages = Array.isArray(answer?.images) ? answer.images : []
      const maxOrder = existingImages.reduce(
        (max: number, img: any) => Math.max(max, Number(img.order_index) || 0),
        0
      )

      const uploadedImages: Array<{ image_id: string; order_index: number }> = []
      for (let i = 0; i < files.length; i += 1) {
        const image = await imagesApi.upload(files[i])
        uploadedImages.push({ image_id: image.id, order_index: maxOrder + i + 1 })
      }

      const mergedImages = [
        ...existingImages.map((img: any, index: number) => ({
          image_id: img.image_id,
          order_index: Number(img.order_index) || index + 1,
        })),
        ...uploadedImages,
      ]

      await upsertAnswerImages(mergedImages)
      toast({
        title: '上传成功',
        description: `成功上传 ${files.length} 张答案图片`,
      })
    } catch (error: any) {
      toast({
        title: '上传失败',
        description: error?.message || '答案图片上传失败',
        variant: 'destructive',
      })
    } finally {
      setIsUploadingAnswerImage(false)
    }
  }

  const handleRemoveAnswerImage = async (imageId: string) => {
    const existingImages = Array.isArray(answer?.images) ? answer.images : []
    const rest = existingImages.filter((img: any) => img.image_id !== imageId)
    const normalized = rest.map((img: any, index: number) => ({
      image_id: img.image_id,
      order_index: index + 1,
    }))
    try {
      await upsertAnswerImages(normalized)
      toast({
        title: '已删除',
        description: '答案图片已移除',
      })
    } catch (error: any) {
      toast({
        title: '删除失败',
        description: error?.message || '无法删除答案图片',
        variant: 'destructive',
      })
    }
  }

  const handleStartEditMetadata = () => {
    setMetadata({
      subject: question?.subject || '',
      type: question?.type || '',
      difficulty: question?.difficulty || '',
      book_name: question?.book_name || '',
      chapter_name: question?.chapter_name || '',
      page_no: question?.page_no ? String(question.page_no) : '',
      question_no: question?.question_no || '',
      tags_text: Array.isArray(question?.tags_json) ? question.tags_json.join(', ') : '',
      knowledge_points_text: Array.isArray((question as any)?.knowledge_points_json)
        ? (question as any).knowledge_points_json.join('\n')
        : '',
    })
    setIsEditingMetadata(true)
  }

  const handleSaveMetadata = () => {
    updateMetadataMutation.mutate(metadata)
  }

  const enterEditMode = () => {
    setIsEditMode(true)
    setShowAnswer(true)
    setShowAppendix(true)
    setIsEditingMetadata(true)
    setIsEditingStem(true)
    setIsEditingAnswer(true)
    setIsEditingAppendix(true)
    setStemContent(question?.stem_text || question?.content_text || question?.content || '')
    setAnswerContent(answer?.answer_text || '')
    setAppendixContent(question?.appendix || '')
    setOptionEditor(normalizeOptions(question?.content_json))
    handleStartEditMetadata()
  }

  const exitEditMode = () => {
    setIsEditMode(false)
    setIsEditingMetadata(false)
    setIsEditingStem(false)
    setIsEditingAnswer(false)
    setIsEditingAppendix(false)
  }

  const attemptList = attempts || []
  const progress = progressData?.items?.[0]
  const totalAttempts = attemptList.length
  const correctCount = attemptList.filter((item: any) => item.result === 'CORRECT').length
  const wrongCount = attemptList.filter((item: any) => item.result === 'WRONG').length
  const skippedCount = attemptList.filter((item: any) => item.result === 'SKIPPED').length
  const wrongAttemptsFromPaperSet = attemptList
    .filter((item: any) => item.result === 'WRONG')
    .map((item: any) => {
      const paperSetId = extractPaperSetId(item.review_mode)
      if (!paperSetId) return null
      const paperSet = (wrongPaperSetMap as Record<string, any>)[paperSetId]
      const paperSetDate = paperSet?.created_at || paperSet?.createdAt
      return {
        attemptId: item.id,
        paperSetId,
        paperSetTitle: paperSet?.title || '未知组卷',
        paperSetDate: paperSetDate ? new Date(paperSetDate).toLocaleString() : '-',
        wrongAt: item.occurred_at ? new Date(item.occurred_at).toLocaleString() : '-',
      }
    })
    .filter((item): item is {
      attemptId: string
      paperSetId: string
      paperSetTitle: string
      paperSetDate: string
      wrongAt: string
    } => Boolean(item))
  const errorTagCountMap = attemptList
    .filter((item: any) => item.result === 'WRONG' || item.result === 'PARTIAL')
    .reduce((acc: Record<string, number>, item: any) => {
      const tags: string[] = Array.isArray(item.error_tags) ? item.error_tags : []
      tags.forEach((tag) => {
        acc[tag] = (acc[tag] || 0) + 1
      })
      return acc
    }, {})
  const errorTagStats = Object.entries(errorTagCountMap)
    .map(([tag, count]) => ({
      tag,
      name: ERROR_TAG_LABELS[tag] || tag,
      count,
    }))
    .sort((a, b) => b.count - a.count)

  // 计算掌握率：跳过的不计入，只在有正确或错误记录时计算
  const effectiveAttempts = correctCount + wrongCount
  const masteryRate = effectiveAttempts > 0 ? Math.round((correctCount / effectiveAttempts) * 100) : 0

  // 根据掌握率确定颜色
  const getMasteryRateColor = () => {
    if (effectiveAttempts === 0) return 'text-muted-foreground'
    if (masteryRate >= 80) return 'text-green-600'
    if (masteryRate >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const handleCopyStemWithOptions = async () => {
    const stem = (question?.stem_text || question?.content_text || question?.content || '').trim()
    const options = normalizeOptions(question?.content_json)
    const optionsText = options.map((item) => `${item.key}. ${item.text}`).join('\n')
    const payload = [stem, optionsText].filter(Boolean).join('\n\n').trim()

    if (!payload) {
      toast({
        title: '无可复制内容',
        description: '题干为空',
        variant: 'destructive',
      })
      return
    }

    try {
      await navigator.clipboard.writeText(payload)
      setCopiedPrompt(true)
      setTimeout(() => setCopiedPrompt(false), 1500)
      toast({
        title: '复制成功',
        description: '题干和选项已复制',
      })
    } catch {
      toast({
        title: '复制失败',
        description: '请检查浏览器剪贴板权限',
        variant: 'destructive',
      })
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    )
  }

  if (!question) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">题目未找到</p>
          <Button onClick={() => router.back()} className="mt-4">
            返回
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      <div className="w-64 border-r bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold">题目详情</h2>
        <div className="space-y-4">
          {reviewReturnUrl && (
            <Button
              variant="default"
              className="w-full justify-start"
              onClick={() => {
                sessionStorage.removeItem(REVIEW_RETURN_CONTEXT_KEY)
                router.push(reviewReturnUrl)
              }}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回复习进度
            </Button>
          )}
          {paperSetReturnUrl && (
            <Button
              variant="default"
              className="w-full justify-start"
              onClick={() => {
                sessionStorage.removeItem(PAPER_SET_DETAIL_RETURN_CONTEXT_KEY)
                router.push(paperSetReturnUrl)
              }}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回组卷详情
            </Button>
          )}
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => router.back()}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回列表
          </Button>
          <Button
            variant="outline"
            className="w-full justify-start border-red-600 text-red-600 hover:bg-red-50 hover:text-red-700"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            删除试题
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* 合并的顶部信息卡片 */}
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h1 className="text-2xl font-bold">题目详情</h1>
                  <div className="mt-2 flex flex-wrap gap-2">
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
                    {question.type && <Badge variant="outline">{getQuestionTypeLabel(question.type)}</Badge>}
                    {(question.tags_json || []).map((tag: string) => (
                      <Badge key={tag} variant="outline">{tag}</Badge>
                    ))}
                    {((question as any).knowledge_points_json || []).map((point: string) => (
                      <Badge key={point} variant="secondary">{point}</Badge>
                    ))}
                  </div>
                  <div className="mt-2 text-sm text-muted-foreground">
                    ID: {question.id} · 创建于 {new Date(question.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex gap-2">
                  {!isEditMode ? (
                    <Button variant="outline" size="sm" onClick={enterEditMode}>
                      <Edit className="mr-2 h-4 w-4" />
                      进入编辑页
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" onClick={exitEditMode}>
                      退出编辑页
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>

            {/* 编辑模式 */}
            {isEditingMetadata ? (
              <CardContent>
                <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div>
                    <Label htmlFor="subject" className="text-xs">学科</Label>
                    <Input
                      id="subject"
                      value={metadata.subject}
                      onChange={(e) => setMetadata(prev => ({ ...prev, subject: e.target.value }))}
                      placeholder="学科"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label htmlFor="type" className="text-xs">题型</Label>
                    <Select value={metadata.type} onValueChange={(value) => setMetadata(prev => ({ ...prev, type: value }))}>
                      <SelectTrigger id="type" className="h-8">
                        <SelectValue placeholder="题型" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="MCQ">选择题</SelectItem>
                        <SelectItem value="FILL_BLANK">填空题</SelectItem>
                        <SelectItem value="SHORT_ANSWER">简答题</SelectItem>
                        <SelectItem value="COMPUTATION">计算题</SelectItem>
                        <SelectItem value="PROOF">证明题</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="difficulty" className="text-xs">难度</Label>
                    <Select value={metadata.difficulty} onValueChange={(value) => setMetadata(prev => ({ ...prev, difficulty: value }))}>
                      <SelectTrigger id="difficulty" className="h-8">
                        <SelectValue placeholder="难度" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="EASY">简单</SelectItem>
                        <SelectItem value="MEDIUM">中等</SelectItem>
                        <SelectItem value="HARD">困难</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="question_no" className="text-xs">题号</Label>
                    <Input
                      id="question_no"
                      value={metadata.question_no}
                      onChange={(e) => setMetadata(prev => ({ ...prev, question_no: e.target.value }))}
                      placeholder="题号"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label htmlFor="book_name" className="text-xs">教材</Label>
                    <Input
                      id="book_name"
                      value={metadata.book_name}
                      onChange={(e) => setMetadata(prev => ({ ...prev, book_name: e.target.value }))}
                      placeholder="教材名称"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label htmlFor="chapter_name" className="text-xs">章节</Label>
                    <Input
                      id="chapter_name"
                      value={metadata.chapter_name}
                      onChange={(e) => setMetadata(prev => ({ ...prev, chapter_name: e.target.value }))}
                      placeholder="章节"
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label htmlFor="page_no" className="text-xs">页码</Label>
                    <Input
                      id="page_no"
                      type="number"
                      value={metadata.page_no}
                      onChange={(e) => setMetadata(prev => ({ ...prev, page_no: e.target.value }))}
                      placeholder="页码"
                      className="h-8"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <Label htmlFor="tags_text" className="text-xs">标签（逗号分隔）</Label>
                    <Input
                      id="tags_text"
                      value={metadata.tags_text}
                      onChange={(e) => setMetadata(prev => ({ ...prev, tags_text: e.target.value }))}
                      placeholder="例如：函数,导数,高考"
                      className="h-8"
                    />
                  </div>
                  <div className="sm:col-span-4">
                    <Label htmlFor="knowledge_points_text" className="text-xs">知识点（支持逗号/、、、/换行，自动拆分）</Label>
                    <Textarea
                      id="knowledge_points_text"
                      value={metadata.knowledge_points_text}
                      onChange={(e) => setMetadata(prev => ({ ...prev, knowledge_points_text: e.target.value }))}
                      placeholder="例如：导数、、、单调性；或每行一个；支持“✅ 总结：本题核心知识点”"
                      rows={3}
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleSaveMetadata}
                    disabled={updateMetadataMutation.isPending}
                    size="sm"
                  >
                    <Save className="mr-2 h-4 w-4" />
                    {updateMetadataMutation.isPending ? '保存中...' : '保存'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsEditingMetadata(false)
                      setMetadata({
                        subject: question?.subject || '',
                        type: question?.type || '',
                        difficulty: question?.difficulty || '',
                        book_name: question?.book_name || '',
                        chapter_name: question?.chapter_name || '',
                        page_no: question?.page_no ? String(question.page_no) : '',
                        question_no: question?.question_no || '',
                        tags_text: Array.isArray(question?.tags_json) ? question.tags_json.join(', ') : '',
                        knowledge_points_text: Array.isArray((question as any)?.knowledge_points_json)
                          ? (question as any).knowledge_points_json.join('\n')
                          : '',
                      })
                    }}
                    size="sm"
                  >
                    <X className="mr-2 h-4 w-4" />
                    取消
                  </Button>
                </div>
              </CardContent>
            ) : (
              /* 查看模式：题目信息 + 掌握情况 */
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <div className="text-xs text-muted-foreground">学科</div>
                    <div className="font-medium text-sm">{question.subject || '-'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">教材/章节</div>
                    <div className="font-medium text-sm">
                      {question.book_name || '-'}
                      {question.chapter_name && ` · ${question.chapter_name}`}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">题号/页码</div>
                    <div className="font-medium text-sm">
                      {question.question_no || '-'}
                      {question.page_no && ` · 第${question.page_no}页`}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">掌握率</div>
                    <div className={`font-semibold text-sm ${getMasteryRateColor()}`}>
                      {masteryRate}%
                      {effectiveAttempts > 0 && (
                        <span className="ml-1 font-normal text-muted-foreground text-xs">
                          ({effectiveAttempts}次)
                        </span>
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">熟练分 / 等级</div>
                    <div className="font-medium text-sm">
                      {progress ? `${progress.proficiency_score} / L${progress.mastery_level}` : '-'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">下次复习</div>
                    <div className="font-medium text-sm">
                      {progress?.next_review_at ? new Date(progress.next_review_at).toLocaleString() : '-'}
                    </div>
                  </div>
                </div>

                {/* 掌握情况统计 */}
                <div className="mt-4 grid grid-cols-4 gap-2 rounded-md border p-2">
                  <div className="text-center">
                    <div className="text-xs text-muted-foreground">正确</div>
                    <div className="text-lg font-semibold text-green-600">{correctCount}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-muted-foreground">错误</div>
                    <div className="text-lg font-semibold text-red-600">{wrongCount}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-muted-foreground">跳过</div>
                    <div className="text-lg font-semibold text-gray-600">{skippedCount}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-muted-foreground">总计</div>
                    <div className="text-lg font-semibold">{totalAttempts}</div>
                  </div>
                </div>

                {errorTagStats.length > 0 && (
                  <div className="mt-4 rounded-md border p-3">
                    <div className="mb-2 text-sm font-medium">历史错因统计（本题）</div>
                    <div className="flex flex-wrap gap-2">
                      {errorTagStats.map((item) => (
                        <Badge key={item.tag} variant="outline">
                          {item.name} x {item.count}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {wrongAttemptsFromPaperSet.length > 0 && (
                  <div className="mt-4 rounded-md border p-3">
                    <div className="mb-2 text-sm font-medium">组卷错题来源</div>
                    <div className="space-y-2">
                      {wrongAttemptsFromPaperSet.map((item) => (
                        <div key={item.attemptId} className="rounded border bg-muted/20 p-2 text-xs">
                          <div>组卷：{item.paperSetTitle}</div>
                          <div>ID：{item.paperSetId}</div>
                          <div>组卷日期：{item.paperSetDate}</div>
                          <div>错误时间：{item.wrongAt}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 快速标记按钮 */}
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    onClick={() => createAttemptMutation.mutate('CORRECT')}
                    disabled={createAttemptMutation.isPending}
                    className="h-7 bg-green-600 hover:bg-green-700"
                  >
                    ✓ 正确
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => createAttemptMutation.mutate('WRONG')}
                    disabled={createAttemptMutation.isPending}
                    className="h-7 border-red-600 text-red-600 hover:bg-red-50"
                  >
                    ✗ 错误
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => createAttemptMutation.mutate('PARTIAL')}
                    disabled={createAttemptMutation.isPending}
                    className="h-7"
                  >
                    ≈ 半对
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => createAttemptMutation.mutate('SKIPPED')}
                    disabled={createAttemptMutation.isPending}
                    className="h-7"
                  >
                    → 跳过
                  </Button>
                </div>
              </CardContent>
            )}
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>题干</CardTitle>
              <div className="flex gap-2">
                {!isEditingStem && (
                  <Button variant="outline" size="sm" onClick={handleStartEditStem}>
                    <Edit className="mr-2 h-4 w-4" />
                    编辑
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={handleCopyStemWithOptions}>
                  {copiedPrompt ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
                  {copiedPrompt ? '已复制' : '复制题干+选项'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {isEditingStem ? (
                <div className="space-y-4">
                  <Textarea
                    value={stemContent}
                    onChange={(e) => setStemContent(e.target.value)}
                    placeholder="编辑题干..."
                    rows={10}
                    className="font-mono"
                  />
                  {(question.type === 'MCQ' || question.type === 'SINGLE_CHOICE' || question.type === 'MULTIPLE_CHOICE' || optionEditor.length > 0) && (
                    <div className="space-y-2 rounded-md border p-3">
                      <div className="mb-2 flex items-center justify-between">
                        <Label className="text-sm">选项编辑</Label>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setOptionEditor((prev) => [...prev, { key: String.fromCharCode(65 + prev.length), text: '' }])}
                        >
                          <Plus className="mr-1 h-3 w-3" />
                          新增
                        </Button>
                      </div>
                      {optionEditor.map((item, index) => (
                        <div key={`${item.key}-${index}`} className="grid grid-cols-[90px_1fr_auto] gap-2">
                          <Input
                            value={item.key}
                            onChange={(e) =>
                              setOptionEditor((prev) => prev.map((opt, i) => (i === index ? { ...opt, key: e.target.value } : opt)))
                            }
                          />
                          <Input
                            value={item.text}
                            onChange={(e) =>
                              setOptionEditor((prev) => prev.map((opt, i) => (i === index ? { ...opt, text: e.target.value } : opt)))
                            }
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            disabled={optionEditor.length <= 1}
                            onClick={() => setOptionEditor((prev) => prev.filter((_, i) => i !== index))}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                  {/* 图片上传区域 */}
                  <div>
                    <input
                      ref={stemImageInputRef}
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={async (e) => {
                        const files = Array.from(e.target.files || [])
                        if (files.length > 0) {
                          setIsUploadingStemImage(true)
                          try {
                            for (const file of files) {
                              const image = await imagesApi.upload(file)
                              await questionsApi.addImage(questionId, image.id)
                            }
                            queryClient.invalidateQueries({ queryKey: ['question', questionId] })
                            toast({
                              title: '上传成功',
                              description: `成功上传 ${files.length} 张图片`,
                            })
                          } catch (error) {
                            toast({
                              title: '上传失败',
                              description: '图片上传失败',
                              variant: 'destructive',
                            })
                          } finally {
                            setIsUploadingStemImage(false)
                          }
                        }
                      }}
                      className="hidden"
                      id="stem-image-input"
                    />
                    <label htmlFor="stem-image-input">
                      <Button type="button" variant="outline" size="sm" asChild disabled={isUploadingStemImage}>
                        <span className="cursor-pointer">
                          <Upload className="mr-2 h-4 w-4" />
                          {isUploadingStemImage ? '上传中...' : '上传图片'}
                        </span>
                      </Button>
                    </label>
                  </div>
                  {/* 现有图片列表 */}
                  {question.stem_images && question.stem_images.length > 0 && (
                    <div className="grid grid-cols-4 gap-3">
                      {question.stem_images.map((image: any) => (
                        <div key={image.image_id} className="relative group">
                          <img
                            src={image.url}
                            alt={`题干图片 ${image.order_index}`}
                            className="w-full h-auto rounded-lg border"
                          />
                          <Button
                            type="button"
                            size="icon"
                            variant="destructive"
                            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={async () => {
                              if (confirm('确定要删除这张图片吗？')) {
                                await questionsApi.removeImage(questionId, image.image_id)
                                queryClient.invalidateQueries({ queryKey: ['question', questionId] })
                              }
                            }}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button
                      onClick={handleSaveStem}
                      disabled={updateStemMutation.isPending}
                      size="sm"
                    >
                      <Save className="mr-2 h-4 w-4" />
                      {updateStemMutation.isPending ? '保存中...' : '保存'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setIsEditingStem(false)
                        setStemContent(
                          question.stem_text || question.content_text || question.content || ''
                        )
                      }}
                      size="sm"
                    >
                      <X className="mr-2 h-4 w-4" />
                      取消
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <LatexContent
                    text={question.stem_text || question.content_text || question.content || ''}
                    className="prose prose-sm max-w-none whitespace-pre-wrap"
                  />
                  {normalizeOptions(question.content_json).length > 0 && (
                    <div className="space-y-2 rounded-md border bg-muted/20 p-3">
                      {normalizeOptions(question.content_json).map((option) => (
                        <div key={option.key} className="flex gap-2 text-sm">
                          <span className="font-medium">{option.key}.</span>
                          <LatexContent text={option.text} className="whitespace-pre-wrap" />
                        </div>
                      ))}
                    </div>
                  )}
                  {/* 题干图片显示 */}
                  {question.stem_images && question.stem_images.length > 0 && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {question.stem_images.map((image: any) => (
                        <img
                          key={image.image_id}
                          src={image.url}
                          alt={`题干图片 ${image.order_index}`}
                          className="w-full h-auto rounded-lg border"
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>答案</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAnswer(!showAnswer)}
                >
                  {showAnswer ? (
                    <>
                      <EyeOff className="mr-2 h-4 w-4" />
                      隐藏
                    </>
                  ) : (
                    <>
                      <Eye className="mr-2 h-4 w-4" />
                      显示
                    </>
                  )}
                </Button>
                {showAnswer && !isEditingAnswer && (
                  <Button variant="outline" size="sm" onClick={handleStartEditAnswer}>
                    <Edit className="mr-2 h-4 w-4" />
                    编辑
                  </Button>
                )}
              </div>
            </CardHeader>
            {showAnswer && (
              <CardContent>
                {isEditingAnswer ? (
                  <div className="space-y-4">
                    <Textarea
                      value={answerContent}
                      onChange={(e) => setAnswerContent(e.target.value)}
                      placeholder="编辑答案..."
                      rows={8}
                      className="font-mono"
                    />
                    <div className="space-y-3">
                      <input
                        ref={answerImageInputRef}
                        type="file"
                        accept="image/*"
                        multiple
                        className="hidden"
                        id="answer-image-input"
                        onChange={async (e) => {
                          const inputEl = e.currentTarget
                          const files = Array.from(inputEl.files || [])
                          await handleUploadAnswerImages(files)
                          inputEl.value = ''
                        }}
                      />
                      <label htmlFor="answer-image-input">
                        <Button type="button" variant="outline" size="sm" asChild disabled={isUploadingAnswerImage}>
                          <span className="cursor-pointer">
                            <Upload className="mr-2 h-4 w-4" />
                            {isUploadingAnswerImage ? '上传中...' : '上传答案图片'}
                          </span>
                        </Button>
                      </label>
                      {Array.isArray(answer?.images) && answer.images.length > 0 && (
                        <div className="grid grid-cols-3 gap-3">
                          {answer.images.map((image: any, index: number) => (
                            <div key={image.image_id || index} className="group relative">
                              <img
                                src={image.url}
                                alt={`答案图片 ${index + 1}`}
                                className="h-auto w-full rounded-lg border"
                              />
                              <Button
                                type="button"
                                size="icon"
                                variant="destructive"
                                className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100"
                                onClick={() => handleRemoveAnswerImage(image.image_id)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  <div className="flex gap-2">
                      <Button
                        onClick={handleSaveAnswer}
                        disabled={updateAnswerMutation.isPending}
                        size="sm"
                      >
                        <Save className="mr-2 h-4 w-4" />
                        {updateAnswerMutation.isPending ? '保存中...' : '保存'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setIsEditingAnswer(false)
                          setAnswerContent(answer?.answer_text || '')
                        }}
                        size="sm"
                      >
                        <X className="mr-2 h-4 w-4" />
                        取消
                      </Button>
                  </div>
                </div>
              ) : (
                  <div className="space-y-4">
                    {answer?.answer_text && (
                      <LatexContent
                        text={answer.answer_text}
                        className="prose prose-sm max-w-none whitespace-pre-wrap"
                      />
                    )}
                    {answer?.images && answer.images.length > 0 && (
                      <div className="space-y-3">
                        {answer.images.map((image: any, index: number) => (
                          <img
                            key={image.image_id || index}
                            src={image.url}
                            alt={`答案图片 ${index + 1}`}
                            className="max-w-full h-auto rounded-lg border"
                          />
                        ))}
                      </div>
                    )}
                    {!answer?.answer_text && (!answer?.images || answer.images.length === 0) && (
                      <div className="text-muted-foreground italic">暂无答案</div>
                    )}
                  </div>
                )}
              </CardContent>
            )}
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>附录</CardTitle>
                <div className="flex gap-2">
                  {!isEditingAppendix && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowAppendix(!showAppendix)}
                    >
                      {showAppendix ? (
                        <>
                          <EyeOff className="mr-2 h-4 w-4" />
                          隐藏
                        </>
                      ) : (
                        <>
                          <Eye className="mr-2 h-4 w-4" />
                          显示
                        </>
                      )}
                    </Button>
                  )}
                  {showAppendix && !isEditingAppendix && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setIsEditingAppendix(true)
                        setAppendixContent(question.appendix || '')
                      }}
                    >
                      <Edit className="mr-2 h-4 w-4" />
                      编辑
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            {showAppendix && (
              <CardContent>
                {isEditingAppendix ? (
                  <div className="space-y-4">
                    <Textarea
                      value={appendixContent}
                      onChange={(e) => setAppendixContent(e.target.value)}
                      placeholder="编辑附录..."
                      rows={8}
                      className="font-mono"
                    />
                    <div className="flex gap-2">
                      <Button onClick={handleSaveAppendix} disabled={updateAppendixMutation.isPending} size="sm">
                        <Save className="mr-2 h-4 w-4" />
                        {updateAppendixMutation.isPending ? '保存中...' : '保存'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setIsEditingAppendix(false)
                          setAppendixContent(question.appendix || '')
                        }}
                        size="sm"
                      >
                        <X className="mr-2 h-4 w-4" />
                        取消
                      </Button>
                    </div>
                  </div>
                ) : (
                  <LatexContent
                    text={question.appendix || '无附录'}
                    className="prose prose-sm max-w-none whitespace-pre-wrap"
                  />
                )}
              </CardContent>
            )}
          </Card>
        </div>
      </div>

      {/* 删除确认对话框 */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除试题</AlertDialogTitle>
            <AlertDialogDescription>
              此操作将删除该试题，删除后无法恢复。确定要继续吗？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteQuestionMutation.mutate()}
              className="bg-red-600 hover:bg-red-700"
              disabled={deleteQuestionMutation.isPending}
            >
              {deleteQuestionMutation.isPending ? '删除中...' : '确认删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
