'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { questionsApi, imagesApi } from '@/lib/api'
import type { AnswerUpdateRequest } from '@/lib/api/answers'
import { useToast } from '@/lib/hooks/use-toast'
import { parseLabels } from '@/lib/label-parser'
import { questionDraft } from '@/lib/question-draft'
import { useAuthStore } from '@/lib/store/auth'
import { ImageRecognitionDialog } from '@/components/image-recognition-dialog'
import { LatexContent } from '@/components/latex-content'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Camera, Check, Copy, Eye, EyeOff, Image as ImageIcon, Plus, Save, X } from 'lucide-react'

type OptionItem = {
  key: string
  text: string
}

type FormData = {
  subject: string
  type: string
  difficulty: string
  stemText: string
  appendix: string
  answerText: string
  stemImages: File[]
  answerImages: File[]
  recognizedStemImageIds: string[]
  options: OptionItem[]
  tags: string[]
  knowledgePoints: string[]
  bookName: string
  chapterName: string
  pageNo: string
  questionNo: string
  contentJson: Record<string, any>
}

const EMPTY_OPTION = (index = 0): OptionItem => ({
  key: String.fromCharCode(65 + index),
  text: '',
})

const EXAMPLE_PREFIX_STORAGE_KEY = 'extract_question_no_auto_example_prefix'

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

const emptyForm = (): FormData => ({
    subject: '',
    type: '',
    difficulty: '',
    stemText: '',
    appendix: '',
    answerText: '',
    stemImages: [],
    answerImages: [],
    recognizedStemImageIds: [],
    options: [EMPTY_OPTION(0), EMPTY_OPTION(1), EMPTY_OPTION(2), EMPTY_OPTION(3)],
    tags: [],
    knowledgePoints: [],
    bookName: '',
    chapterName: '',
    pageNo: '',
    questionNo: '',
    contentJson: {},
  })

type QuestionDraft = {
  version: 1
  form: FormData
  tagInput: string
  knowledgePointInput: string
  includeRecognizedStemImages: boolean
  stemUploadIds: Array<string | null>
  answerUploadIds: Array<string | null>
  pendingSave: { payload: string; requestId: string } | null
}

export default function ExtractPage() {
  const router = useRouter()
  const { toast } = useToast()

  const accountId = useAuthStore((state) => state.user?.id)
  const [formData, setFormData] = useState<FormData>(emptyForm)

  const [tagInput, setTagInput] = useState('')
  const [knowledgePointInput, setKnowledgePointInput] = useState('')
  const [includeRecognizedStemImages, setIncludeRecognizedStemImages] = useState(false)
  const [showImageDialog, setShowImageDialog] = useState(false)
  const [stemPreviewUrls, setStemPreviewUrls] = useState<string[]>([])
  const [answerPreviewUrls, setAnswerPreviewUrls] = useState<string[]>([])
  const [showStemPreview, setShowStemPreview] = useState(false)
  const [showAnswerPreview, setShowAnswerPreview] = useState(false)
  const [showOptionPreview, setShowOptionPreview] = useState(false)
  const [isStemDragActive, setIsStemDragActive] = useState(false)
  const [isAnswerDragActive, setIsAnswerDragActive] = useState(false)
  const [isAiDragActive, setIsAiDragActive] = useState(false)
  const [aiModel, setAiModel] = useState('qwen3-vl-flash')
  const [autoRecognizeFiles, setAutoRecognizeFiles] = useState<File[] | null>(null)
  const [copiedPrompt, setCopiedPrompt] = useState(false)
  const [autoExamplePrefix, setAutoExamplePrefix] = useState(false)
  const uploadedFiles = useRef(new WeakMap<File, Promise<string>>())
  const uploadedImageIds = useRef(new WeakMap<File, string>())
  const pendingSave = useRef<{ payload: string; requestId: string } | null>(null)
  const questionSaved = useRef(false)
  const [draftReady, setDraftReady] = useState(false)
  const [draftStatus, setDraftStatus] = useState('正在读取草稿…')
  const draftReadyRef = useRef(false)
  draftReadyRef.current = draftReady
  const latestDraft = useRef({ form: formData, tagInput, knowledgePointInput, includeRecognizedStemImages })
  latestDraft.current = { form: formData, tagInput, knowledgePointInput, includeRecognizedStemImages }
  const hasDraftContent = Boolean(tagInput || knowledgePointInput || Object.entries(formData).some(([key, value]) => {
    if (key === 'options') return formData.options.some((option) => option.text)
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return Boolean(value)
  }))
  const hasDraftRef = useRef(false)
  hasDraftRef.current = hasDraftContent

  const persistDraft = async () => {
    if (!accountId || questionSaved.current || !draftReadyRef.current || !hasDraftRef.current) return
    const current = latestDraft.current
    const draft: QuestionDraft = {
      version: 1, ...current,
      stemUploadIds: current.form.stemImages.map((file) => uploadedImageIds.current.get(file) ?? null),
      answerUploadIds: current.form.answerImages.map((file) => uploadedImageIds.current.get(file) ?? null),
      pendingSave: pendingSave.current,
    }
    await questionDraft.save(accountId, draft)
  }

  useEffect(() => {
    if (!accountId) return
    let active = true
    void questionDraft.read<QuestionDraft>(accountId).then((draft) => {
      if (!active) return
      if (draft) {
        if (draft.version !== 1 || !draft.form) throw new Error('Invalid draft')
        const restoreFiles = (files: File[], ids: Array<string | null>) => files.map((file, index) => {
          if (!(file instanceof Blob)) throw new Error('Invalid draft image')
          const restored = new File([file], file.name || 'image', { type: file.type, lastModified: file.lastModified })
          if (ids[index]) {
            uploadedImageIds.current.set(restored, ids[index]!)
            uploadedFiles.current.set(restored, Promise.resolve(ids[index]!))
          }
          return restored
        })
        const restored = { ...emptyForm(), ...draft.form,
          stemImages: restoreFiles(draft.form.stemImages, draft.stemUploadIds),
          answerImages: restoreFiles(draft.form.answerImages, draft.answerUploadIds),
        }
        setFormData(restored)
        setTagInput(draft.tagInput)
        setKnowledgePointInput(draft.knowledgePointInput)
        setIncludeRecognizedStemImages(draft.includeRecognizedStemImages)
        pendingSave.current = draft.pendingSave
        setDraftStatus('已恢复上次草稿，包含所选图片')
      } else setDraftStatus('填写后会自动保存草稿')
      setDraftReady(true)
    }).catch(() => {
      if (active) {
        setDraftStatus('草稿读取失败，仍可录题；请勿刷新未保存的内容')
        setDraftReady(true)
      }
    })
    return () => { active = false }
  }, [accountId])

  useEffect(() => {
    if (!draftReady || !hasDraftContent || questionSaved.current) return
    let active = true
    setDraftStatus('正在保存草稿…')
    const timer = window.setTimeout(() => {
      void persistDraft().then(() => { if (active) setDraftStatus('草稿已自动保存，刷新后可恢复文字和图片') })
        .catch(() => { if (active) setDraftStatus('草稿保存失败，请先保存试题再离开页面') })
    }, 500)
    return () => { active = false; window.clearTimeout(timer) }
  }, [formData, tagInput, knowledgePointInput, includeRecognizedStemImages, draftReady, hasDraftContent])

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!questionSaved.current && hasDraftRef.current) {
        event.preventDefault()
        event.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', warn)
    return () => {
      window.removeEventListener('beforeunload', warn)
      void persistDraft().catch(() => undefined)
    }
  }, [accountId])

  const discardDraft = async () => {
    if (!accountId || !window.confirm('清空当前草稿及所选图片？')) return
    questionSaved.current = true
    try {
      await questionDraft.remove(accountId)
      setFormData(emptyForm())
      setTagInput('')
      setKnowledgePointInput('')
      setIncludeRecognizedStemImages(false)
      pendingSave.current = null
      uploadedFiles.current = new WeakMap()
      uploadedImageIds.current = new WeakMap()
      setDraftStatus('草稿已清空')
    } catch {
      toast({ title: '清空草稿失败', variant: 'destructive' })
    } finally {
      questionSaved.current = false
    }
  }

  const uploadOnce = (file: File): Promise<string> => {
    const cached = uploadedFiles.current.get(file)
    if (cached) return cached
    const upload = imagesApi.upload(file).then((image) => {
      uploadedImageIds.current.set(file, image.id)
      return image.id
    }).catch((error) => {
      uploadedFiles.current.delete(file)
      throw error
    })
    uploadedFiles.current.set(file, upload)
    return upload
  }

  useEffect(() => {
    const saved = localStorage.getItem(EXAMPLE_PREFIX_STORAGE_KEY)
    if (saved === '1') {
      setAutoExamplePrefix(true)
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(EXAMPLE_PREFIX_STORAGE_KEY, autoExamplePrefix ? '1' : '0')
  }, [autoExamplePrefix])

  const normalizeQuestionNo = (value: string) => {
    if (!autoExamplePrefix) return value
    const trimmed = value.trim()
    if (!trimmed || trimmed.startsWith('例')) return value
    return `例${trimmed}`
  }

  const { data: commonTags = [] } = useQuery({
    queryKey: ['common-tags'],
    queryFn: () => questionsApi.getCommonTags(4),
    retry: false,
    staleTime: Infinity,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const pendingKnowledgePoints = parseLabels(knowledgePointInput)
      const finalKnowledgePoints = Array.from(
        new Set([...formData.knowledgePoints, ...pendingKnowledgePoints])
      )

      if (
        !formData.subject ||
        !formData.type ||
        (!formData.stemText &&
          formData.stemImages.length === 0 &&
          !(includeRecognizedStemImages && formData.recognizedStemImageIds.length > 0))
      ) {
        throw new Error('请填写学科、题型，且至少提供题干文本或题干图片')
      }

      const uploadedStemIds: string[] = []
      for (const file of formData.stemImages) {
        uploadedStemIds.push(await uploadOnce(file))
      }
      const uploadedAnswerIds: string[] = []
      for (const file of formData.answerImages) {
        uploadedAnswerIds.push(await uploadOnce(file))
      }
      const stemImageIds = Array.from(new Set([
        ...(includeRecognizedStemImages ? formData.recognizedStemImageIds : []),
        ...uploadedStemIds,
      ]))
      const answerImages = Array.from(new Set(uploadedAnswerIds)).map((image_id, order_index) => ({
        image_id, order_index,
      }))

      const finalOptions = formData.options
        .map((opt) => ({ key: opt.key.trim(), text: opt.text.trim() }))
        .filter((opt) => opt.key && opt.text)

      const isChoiceType = ['MCQ', 'SINGLE_CHOICE', 'MULTIPLE_CHOICE'].includes(formData.type.toUpperCase())
      const contentJson = {
        ...(formData.contentJson || {}),
        ...(isChoiceType ? { options: finalOptions } : {}),
      }

      const question = {
        subject: formData.subject,
        type: formData.type,
        difficulty: formData.difficulty || null,
        stem_text: formData.stemText || null,
        stem_latex: null,
        appendix: formData.appendix || null,
        content_json: contentJson,
        paper_meta: {},
        tags_json: Array.from(new Set([...formData.tags, ...parseLabels(tagInput)])),
        knowledge_points_json: finalKnowledgePoints,
        book_name: formData.bookName || null,
        chapter_name: formData.chapterName || null,
        page_no: formData.pageNo ? Number(formData.pageNo) : null,
        question_no: formData.questionNo || null,
        stem_image_ids: stemImageIds,
      }
      const answer: AnswerUpdateRequest | null = formData.answerText || answerImages.length > 0
        ? {
            answer_type: formData.answerText ? (answerImages.length > 0 ? 'MIXED' : 'TEXT') : 'IMAGE',
            answer_text: formData.answerText || null,
            images: answerImages,
          }
        : null
      const payload = JSON.stringify({ question, answer })
      // Keep the same ID after a lost response; edited content starts a new submission.
      if (pendingSave.current?.payload !== payload) {
        pendingSave.current = { payload, requestId: crypto.randomUUID() }
      }
      // Persist upload IDs and the request ID before sending, for a reload after a lost response.
      await persistDraft().catch(() => setDraftStatus('草稿保存失败，请勿刷新页面'))
      return questionsApi.createWithAnswer({
        request_id: pendingSave.current.requestId,
        question,
        answer,
      })
    },
    onSuccess: async () => {
      questionSaved.current = true
      let cleared = true
      if (accountId) await questionDraft.remove(accountId).catch(() => { cleared = false })
      toast({ title: '成功', description: cleared ? '试题录入成功' : '试题已保存，但本机草稿未能清理，请手动清空草稿' })
      router.push('/dashboard/questions')
    },
    onError: (error: any) => {
      toast({
        title: '提交失败',
        description: error?.message || '试题录入失败',
        variant: 'destructive',
      })
    },
  })

  const isChoiceType = useMemo(
    () => ['MCQ', 'SINGLE_CHOICE', 'MULTIPLE_CHOICE'].includes((formData.type || '').toUpperCase()),
    [formData.type],
  )

  const addTag = (tag: string) => {
    const values = parseLabels(tag)
    if (values.length === 0) return
    setFormData((prev) => ({ ...prev, tags: Array.from(new Set([...prev.tags, ...values])) }))
  }

  const removeTag = (tag: string) => {
    setFormData((prev) => ({ ...prev, tags: prev.tags.filter((t) => t !== tag) }))
  }

  const addKnowledgePoints = (raw: string) => {
    const values = parseLabels(raw)
    if (values.length === 0) return
    setFormData((prev) => ({
      ...prev,
      knowledgePoints: Array.from(new Set([...prev.knowledgePoints, ...values])),
    }))
  }

  const removeKnowledgePoint = (point: string) => {
    setFormData((prev) => ({
      ...prev,
      knowledgePoints: prev.knowledgePoints.filter((item) => item !== point),
    }))
  }

  const updateOption = (index: number, patch: Partial<OptionItem>) => {
    setFormData((prev) => ({
      ...prev,
      options: prev.options.map((opt, i) => (i === index ? { ...opt, ...patch } : opt)),
    }))
  }

  const addOption = () => {
    setFormData((prev) => ({ ...prev, options: [...prev.options, EMPTY_OPTION(prev.options.length)] }))
  }

  const removeOption = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index),
    }))
  }

  const handleImageRecognized = (data: any) => {
    const recognizedOptions = normalizeOptions(data?.content_json)
    const recognizedKnowledgePoints = parseLabels(
      Array.isArray(data?.knowledge_points_json)
        ? data.knowledge_points_json.join('\n')
        : Array.isArray(data?.knowledge_points)
        ? data.knowledge_points.join('\n')
        : data?.knowledge_points || ''
    )
    setFormData((prev) => ({
      ...prev,
      subject: data.subject || prev.subject,
      type: data.type || (recognizedOptions.length > 0 ? 'MCQ' : prev.type),
      difficulty: data.difficulty || prev.difficulty,
      stemText: data.stem_text || prev.stemText,
      appendix: data.appendix || prev.appendix,
      answerText: data.answer_text || prev.answerText,
      tags: Array.isArray(data.tags) ? data.tags : prev.tags,
      knowledgePoints:
        recognizedKnowledgePoints.length > 0
          ? Array.from(new Set([...prev.knowledgePoints, ...recognizedKnowledgePoints]))
          : prev.knowledgePoints,
      bookName: data.book_name || prev.bookName,
      chapterName: data.chapter_name || prev.chapterName,
      recognizedStemImageIds: Array.isArray(data.stem_image_ids) ? data.stem_image_ids : prev.recognizedStemImageIds,
      contentJson: typeof data.content_json === 'object' && data.content_json ? data.content_json : prev.contentJson,
      options: recognizedOptions.length > 0 ? recognizedOptions : prev.options,
    }))

    toast({ title: '识别成功', description: '已自动填充，建议你检查后再保存。' })
  }

  const appendStemFiles = (files: File[]) => {
    const imageFiles = files.filter((file) => file.type.startsWith('image/'))
    if (imageFiles.length === 0) return
    setFormData((prev) => ({ ...prev, stemImages: [...prev.stemImages, ...imageFiles] }))
    setStemPreviewUrls((prev) => [...prev, ...imageFiles.map((f) => URL.createObjectURL(f))])
  }

  const appendAnswerFiles = (files: File[]) => {
    const imageFiles = files.filter((file) => file.type.startsWith('image/'))
    if (imageFiles.length === 0) return
    setFormData((prev) => ({ ...prev, answerImages: [...prev.answerImages, ...imageFiles] }))
    setAnswerPreviewUrls((prev) => [...prev, ...imageFiles.map((f) => URL.createObjectURL(f))])
  }

  const openRecognitionWithFiles = (files: File[]) => {
    const imageFiles = files.filter((file) => file.type.startsWith('image/'))
    if (imageFiles.length === 0) return
    setAutoRecognizeFiles(imageFiles)
    setShowImageDialog(true)
  }

  const handleCopyStemWithOptions = async () => {
    const stem = (formData.stemText || '').trim()
    const options = formData.options
      .map((opt) => ({ key: opt.key.trim(), text: opt.text.trim() }))
      .filter((opt) => opt.key && opt.text)
    const optionsText = options.map((item) => `${item.key}. ${item.text}`).join('\n')
    const payload = [stem, optionsText].filter(Boolean).join('\n\n').trim()

    if (!payload) {
      toast({
        title: '无可复制内容',
        description: '题干和选项都为空',
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

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">录入试题</h1>
          <p className="text-muted-foreground">支持手动录入与图片识别</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/dashboard/questions')}>
            取消
          </Button>
          <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !draftReady}>
            <Save className="mr-2 h-4 w-4" />
            {createMutation.isPending ? '保存中...' : '保存试题'}
          </Button>
        </div>
      </div>

      <div className="mb-6 flex items-center justify-between gap-4 rounded-lg border bg-muted/40 px-4 py-3">
        <p role="status" className="text-sm text-muted-foreground">{draftStatus}</p>
        <Button variant="ghost" size="sm" onClick={discardDraft} disabled={!draftReady || createMutation.isPending}>清空草稿</Button>
      </div>

      <fieldset disabled={createMutation.isPending || !draftReady} className="mx-auto max-w-4xl space-y-6 disabled:pointer-events-none">
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="subject">学科 *</Label>
                <Input id="subject" value={formData.subject} onChange={(e) => setFormData((p) => ({ ...p, subject: e.target.value }))} />
              </div>

              <div>
                <Label htmlFor="type">题型 *</Label>
                <Select value={formData.type} onValueChange={(value) => setFormData((p) => ({ ...p, type: value }))}>
                  <SelectTrigger id="type">
                    <SelectValue placeholder="选择题型" />
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
                <Label htmlFor="difficulty">难度</Label>
                <Select value={formData.difficulty} onValueChange={(value) => setFormData((p) => ({ ...p, difficulty: value }))}>
                  <SelectTrigger id="difficulty">
                    <SelectValue placeholder="选择难度" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EASY">简单</SelectItem>
                    <SelectItem value="MEDIUM">中等</SelectItem>
                    <SelectItem value="HARD">困难</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <Label htmlFor="questionNo" className="mb-0">题号</Label>
                  <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                    <Checkbox
                      checked={autoExamplePrefix}
                      onCheckedChange={(checked) => setAutoExamplePrefix(checked === true)}
                    />
                    记忆在本地：自动补“例”
                  </label>
                </div>
                <Input
                  id="questionNo"
                  placeholder={autoExamplePrefix ? '输入 5.1 会自动变为 例5.1' : undefined}
                  value={formData.questionNo}
                  onChange={(e) =>
                    setFormData((p) => ({
                      ...p,
                      questionNo: normalizeQuestionNo(e.target.value),
                    }))
                  }
                />
              </div>
            </div>

            <div>
              <Label htmlFor="tagInput">标签</Label>
              <div className="space-y-2">
                <Input
                  id="tagInput"
                  placeholder="输入标签后回车"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addTag(tagInput)
                      setTagInput('')
                    }
                  }}
                />
                {commonTags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {commonTags.map((tag) => (
                      <Badge key={tag} variant={formData.tags.includes(tag) ? 'default' : 'outline'} className="cursor-pointer" onClick={() => (formData.tags.includes(tag) ? removeTag(tag) : addTag(tag))}>
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
                {formData.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formData.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="gap-1">
                        {tag}
                        <X className="h-3 w-3 cursor-pointer" onClick={() => removeTag(tag)} />
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <Label htmlFor="knowledgePointInput">知识点</Label>
              <div className="space-y-2">
                <Textarea
                  id="knowledgePointInput"
                  placeholder="可粘贴：导数、、、单调性；或每行一个；支持“✅ 总结：本题核心知识点”格式"
                  value={knowledgePointInput}
                  onChange={(e) => setKnowledgePointInput(e.target.value)}
                  rows={3}
                />
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      addKnowledgePoints(knowledgePointInput)
                      setKnowledgePointInput('')
                    }}
                  >
                    自动拆分并添加
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setKnowledgePointInput('')
                      setFormData((prev) => ({ ...prev, knowledgePoints: [] }))
                    }}
                  >
                    清空
                  </Button>
                </div>
                {formData.knowledgePoints.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formData.knowledgePoints.map((point) => (
                      <Badge key={point} variant="secondary" className="gap-1">
                        {point}
                        <X className="h-3 w-3 cursor-pointer" onClick={() => removeKnowledgePoint(point)} />
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>题目来源（可选）</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="bookName">教材/资料</Label>
              <Input id="bookName" value={formData.bookName} onChange={(e) => setFormData((p) => ({ ...p, bookName: e.target.value }))} />
            </div>
            <div>
              <Label htmlFor="chapterName">章节</Label>
              <Input id="chapterName" value={formData.chapterName} onChange={(e) => setFormData((p) => ({ ...p, chapterName: e.target.value }))} />
            </div>
            <div>
              <Label htmlFor="pageNo">页码</Label>
              <Input id="pageNo" type="number" value={formData.pageNo} onChange={(e) => setFormData((p) => ({ ...p, pageNo: e.target.value }))} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle>题干</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={handleCopyStemWithOptions}>
                {copiedPrompt ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
                {copiedPrompt ? '已复制' : '复制题干+选项'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>题干图片</Label>
              <div
                className={`mt-2 space-y-3 rounded-lg border-2 border-dashed p-3 transition-colors ${
                  isStemDragActive ? 'border-primary bg-primary/5' : 'border-border'
                }`}
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsStemDragActive(true)
                }}
                onDragLeave={(e) => {
                  e.preventDefault()
                  setIsStemDragActive(false)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  setIsStemDragActive(false)
                  appendStemFiles(Array.from(e.dataTransfer.files || []))
                }}
              >
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files || [])
                    appendStemFiles(files)
                  }}
                  className="hidden"
                  id="stem-image-input"
                />
                <label htmlFor="stem-image-input" className="inline-flex cursor-pointer items-center rounded-md border px-4 py-2 text-sm hover:bg-accent">
                  <ImageIcon className="mr-2 h-4 w-4" />
                  选择题干图片（可多张）
                </label>
                <p className="text-xs text-muted-foreground">或把图片拖到这个区域上传</p>

                {formData.recognizedStemImageIds.length > 0 && (
                  <div className="space-y-2 rounded-md bg-muted/30 p-2 text-xs text-muted-foreground">
                    <p>已识别到图片 {formData.recognizedStemImageIds.length} 张（默认不会自动放到题干）</p>
                    <label className="flex cursor-pointer items-center gap-2 text-foreground">
                      <Checkbox
                        checked={includeRecognizedStemImages}
                        onCheckedChange={(checked) => setIncludeRecognizedStemImages(Boolean(checked))}
                      />
                      保存时将识别图片关联到题干
                    </label>
                  </div>
                )}

                {stemPreviewUrls.length > 0 && (
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                    {stemPreviewUrls.map((url, index) => (
                      <div key={`${url}-${index}`} className="group relative">
                        <img src={url} alt={`stem-${index + 1}`} className="h-32 w-full rounded-lg border object-cover" />
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100"
                          onClick={() => {
                            setFormData((prev) => ({ ...prev, stemImages: prev.stemImages.filter((_, i) => i !== index) }))
                            setStemPreviewUrls((prev) => prev.filter((_, i) => i !== index))
                          }}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <Label htmlFor="stemText">题干文本</Label>
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowStemPreview((v) => !v)}>
                  {showStemPreview ? <EyeOff className="mr-1 h-3 w-3" /> : <Eye className="mr-1 h-3 w-3" />}
                  {showStemPreview ? '编辑' : '预览'}
                </Button>
              </div>
              {showStemPreview ? (
                <div className="min-h-[120px] rounded-lg border bg-background p-4">
                  <LatexContent text={formData.stemText || '（预览区域）'} className="prose prose-sm max-w-none" />
                </div>
              ) : (
                <Textarea id="stemText" className="min-h-[140px] font-mono" value={formData.stemText} onChange={(e) => setFormData((p) => ({ ...p, stemText: e.target.value }))} />
              )}
            </div>

            <div>
              <Label htmlFor="appendix">附录（可选）</Label>
              <Textarea id="appendix" className="min-h-[80px]" value={formData.appendix} onChange={(e) => setFormData((p) => ({ ...p, appendix: e.target.value }))} />
            </div>
          </CardContent>
        </Card>

        {isChoiceType && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>选项（选择题）</CardTitle>
                <div className="flex gap-2">
                  <Button type="button" variant="ghost" size="sm" onClick={() => setShowOptionPreview((v) => !v)}>
                    {showOptionPreview ? <EyeOff className="mr-1 h-3 w-3" /> : <Eye className="mr-1 h-3 w-3" />}
                    {showOptionPreview ? '编辑' : '预览'}
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={addOption}>
                    <Plus className="mr-1 h-3 w-3" />新增选项
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {formData.options.map((opt, index) => (
                <div key={`opt-${index}`} className="rounded-md border p-3">
                  <div className="mb-2 grid grid-cols-[90px_1fr_auto] gap-2">
                    <Input
                      value={opt.key}
                      onChange={(e) => updateOption(index, { key: e.target.value })}
                      placeholder="A"
                    />
                    <Input
                      value={opt.text}
                      onChange={(e) => updateOption(index, { text: e.target.value })}
                      placeholder="输入选项内容（支持 LaTeX）"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => removeOption(index)}
                      disabled={formData.options.length <= 1}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  {showOptionPreview && (
                    <div className="rounded bg-muted/30 p-2 text-sm">
                      <span className="mr-1 font-medium">{opt.key || '?'}. </span>
                      <LatexContent text={opt.text || '（空）'} className="inline" />
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>答案（可选）</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <Label htmlFor="answerText">答案文本</Label>
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowAnswerPreview((v) => !v)}>
                  {showAnswerPreview ? <EyeOff className="mr-1 h-3 w-3" /> : <Eye className="mr-1 h-3 w-3" />}
                  {showAnswerPreview ? '编辑' : '预览'}
                </Button>
              </div>
              {showAnswerPreview ? (
                <div className="min-h-[80px] rounded-lg border bg-background p-4">
                  <LatexContent text={formData.answerText || '（预览区域）'} className="prose prose-sm max-w-none" />
                </div>
              ) : (
                <Textarea id="answerText" className="min-h-[100px] font-mono" value={formData.answerText} onChange={(e) => setFormData((p) => ({ ...p, answerText: e.target.value }))} />
              )}
            </div>

            <div className="border-t pt-4">
              <Label>答案图片（可多张）</Label>
              <div
                className={`mt-2 space-y-3 rounded-lg border-2 border-dashed p-3 transition-colors ${
                  isAnswerDragActive ? 'border-primary bg-primary/5' : 'border-border'
                }`}
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsAnswerDragActive(true)
                }}
                onDragLeave={(e) => {
                  e.preventDefault()
                  setIsAnswerDragActive(false)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  setIsAnswerDragActive(false)
                  appendAnswerFiles(Array.from(e.dataTransfer.files || []))
                }}
              >
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files || [])
                    appendAnswerFiles(files)
                  }}
                  className="hidden"
                  id="answer-image-input"
                />
                <label htmlFor="answer-image-input" className="inline-flex cursor-pointer items-center rounded-md border px-4 py-2 text-sm hover:bg-accent">
                  <ImageIcon className="mr-2 h-4 w-4" />
                  选择答案图片
                </label>
                <p className="text-xs text-muted-foreground">或把图片拖到这个区域上传</p>

                {answerPreviewUrls.length > 0 && (
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                    {answerPreviewUrls.map((url, index) => (
                      <div key={`${url}-${index}`} className="group relative">
                        <img src={url} alt={`ans-${index + 1}`} className="h-32 w-full rounded-lg border object-cover" />
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100"
                          onClick={() => {
                            setFormData((prev) => ({ ...prev, answerImages: prev.answerImages.filter((_, i) => i !== index) }))
                            setAnswerPreviewUrls((prev) => prev.filter((_, i) => i !== index))
                          }}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2">
                <Camera className="h-5 w-5" />
                图片识别（AI 辅助）
              </CardTitle>
              <div className="w-[220px]">
                <Select value={aiModel} onValueChange={setAiModel}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择识别模型" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="qwen3-vl-flash">通义千问 VL Flash</SelectItem>
                    <SelectItem value="qwen3.5-flash">通义千问 3.5 Flash</SelectItem>
                    <SelectItem value="qwen3-vl-plus">通义千问 VL Plus</SelectItem>
                    <SelectItem value="qwen3.5-plus">通义千问 3.5 Plus</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div
              className={`flex flex-col items-center gap-4 rounded-lg border-2 border-dashed p-8 transition-colors ${
                isAiDragActive ? 'border-primary bg-primary/10' : ''
              }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsAiDragActive(true)
              }}
              onDragLeave={(e) => {
                e.preventDefault()
                setIsAiDragActive(false)
              }}
              onDrop={(e) => {
                e.preventDefault()
                setIsAiDragActive(false)
                openRecognitionWithFiles(Array.from(e.dataTransfer.files || []))
              }}
            >
              <div className="flex gap-3">
                <Button onClick={() => setShowImageDialog(true)}>
                  <Camera className="mr-2 h-4 w-4" />拍照识别
                </Button>
                <Button variant="outline" onClick={() => setShowImageDialog(true)}>
                  <ImageIcon className="mr-2 h-4 w-4" />从相册选择
                </Button>
              </div>
              <p className="text-center text-xs text-muted-foreground">
                可把图片直接拖到此区域识别。识别结果会自动填充题干文本、选项和来源信息，图片不会自动挂到题干。
              </p>
            </div>
          </CardContent>
        </Card>
      </fieldset>

      <ImageRecognitionDialog
        open={showImageDialog}
        onOpenChange={setShowImageDialog}
        onRecognized={handleImageRecognized}
        selectedModel={aiModel}
        onSelectedModelChange={setAiModel}
        autoFiles={autoRecognizeFiles}
        onAutoFilesHandled={() => setAutoRecognizeFiles(null)}
      />
    </div>
  )
}
