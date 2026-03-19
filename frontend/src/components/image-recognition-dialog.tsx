'use client'

import { useEffect, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertCircle,
  Camera,
  Check,
  Image as ImageIcon,
  Loader2,
  Plus,
  Sparkles,
  X,
} from 'lucide-react'
import { imagesApi, extractionsApi } from '@/lib/api'

const AVAILABLE_MODELS = [
  { id: 'qwen3-vl-flash', name: '通义千问 VL Flash', description: '速度快，成本低' },
  { id: 'qwen3.5-flash', name: '通义千问 3.5 Flash', description: '通用性更强' },
  { id: 'qwen3-vl-plus', name: '通义千问 VL Plus', description: '视觉效果更好' },
  { id: 'qwen3.5-plus', name: '通义千问 3.5 Plus', description: '高精度文本能力' },
]

interface RecognizedQuestion {
  subject?: string
  type?: string
  difficulty?: string
  stem_text?: string
  stem_latex?: string
  appendix?: string
  answer_text?: string
  tags?: string[]
  book_name?: string
  chapter_name?: string
  stem_image_ids?: string[]
  content_json?: any
}

interface ImagePreview {
  id: string
  url: string
  file: File
}

interface ImageRecognitionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onRecognized: (data: RecognizedQuestion) => void
  selectedModel?: string
  onSelectedModelChange?: (model: string) => void
  autoFiles?: File[] | null
  onAutoFilesHandled?: () => void
}

function normalizeOptions(raw: any): Array<{ key: string; text: string }> {
  if (!raw) return []

  if (Array.isArray(raw)) {
    return raw
      .map((item: any, index: number) => {
        if (!item || typeof item !== 'object') return null
        const key = String(item.key ?? item.label ?? String.fromCharCode(65 + index)).trim()
        const text = String(item.text ?? item.content ?? '').trim()
        if (!text) return null
        return { key, text }
      })
      .filter((item): item is { key: string; text: string } => Boolean(item))
  }

  if (typeof raw === 'string') {
    return raw
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        const match = line.match(/^([A-Z])[\.、\)]\s*(.*)$/i)
        if (match) return { key: match[1].toUpperCase(), text: match[2] }
        return { key: String.fromCharCode(65 + index), text: line }
      })
  }

  return []
}

function resolveStem(raw: any): string {
  return String(
    raw?.stem_text ?? raw?.stemText ?? raw?.problem ?? raw?.question ?? raw?.stem ?? ''
  ).trim()
}

function resolveAppendix(raw: any): string {
  return String(raw?.appendix ?? '').trim()
}

function resolveChoices(raw: any): Array<{ key: string; text: string }> {
  return normalizeOptions(raw?.content_json?.options ?? raw?.content_json?.choices ?? raw?.options ?? raw?.choices)
}

export function ImageRecognitionDialog({
  open,
  onOpenChange,
  onRecognized,
  selectedModel,
  onSelectedModelChange,
  autoFiles,
  onAutoFilesHandled,
}: ImageRecognitionDialogProps) {
  const [step, setStep] = useState<'select' | 'processing' | 'success' | 'error'>('select')
  const [imagePreviews, setImagePreviews] = useState<ImagePreview[]>([])
  const [uploadedImageIds, setUploadedImageIds] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [clipboardError, setClipboardError] = useState<string | null>(null)
  const [internalModel, setInternalModel] = useState('qwen3-vl-flash')
  const activeModel = selectedModel || internalModel
  const handleModelChange = (value: string) => {
    if (onSelectedModelChange) onSelectedModelChange(value)
    else setInternalModel(value)
  }

  const processFiles = async (files: File[]) => {
    try {
      setStep('processing')
      setError(null)

      const newPreviews: ImagePreview[] = []
      const newImageIds: string[] = []

      for (let i = 0; i < files.length; i += 1) {
        const file = files[i]
        newPreviews.push({
          id: `temp-${Date.now()}-${i}`,
          url: URL.createObjectURL(file),
          file,
        })

        const image = await imagesApi.upload(file)
        newImageIds.push(image.id)
      }

      setImagePreviews((prev) => [...prev, ...newPreviews])
      setUploadedImageIds((prev) => [...prev, ...newImageIds])

      if (newImageIds.length > 0) {
        const { extraction_id } = await extractionsApi.create(newImageIds, activeModel)
        await extractionsApi.retry(extraction_id)
        await pollForResult(extraction_id, newImageIds)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '识别失败，请重试')
      setStep('error')
    }
  }

  const handleFileSelect = async (files: FileList) => {
    await processFiles(Array.from(files))
  }

  useEffect(() => {
    if (!open || step !== 'select' || !autoFiles || autoFiles.length === 0) return
    const imageFiles = autoFiles.filter((f) => f.type.startsWith('image/'))
    onAutoFilesHandled?.()
    if (imageFiles.length > 0) {
      processFiles(imageFiles)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, autoFiles, step])

  const pollForResult = async (extractionId: string, imageIds: string[]) => {
    const maxAttempts = 60

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      try {
        const extraction = await extractionsApi.get(extractionId)
        const status = String((extraction as any)?.status || '').toUpperCase()

        if (status === 'DONE' || status === 'COMPLETED') {
          const draftResponse = await extractionsApi.getDraftQuestions(extractionId)
          const firstQuestion = draftResponse.questions?.[0] as any

          if (!firstQuestion) {
            setError('未识别到题目，请重试')
            setStep('error')
            return
          }

          const stemText = resolveStem(firstQuestion)
          const appendix = resolveAppendix(firstQuestion)
          const options = resolveChoices(firstQuestion)
          const inferredType = options.length > 0 ? 'MCQ' : ''

          setStep('success')
          setTimeout(() => {
            onRecognized({
              subject: '',
              type: inferredType,
              difficulty: '',
              stem_text: stemText,
              stem_latex: stemText.includes('$$') ? stemText : '',
              appendix: appendix || undefined,
              answer_text: '',
              tags: [],
              book_name: '',
              chapter_name: '',
              stem_image_ids: imageIds,
              content_json: options.length > 0 ? { options } : undefined,
            })
            handleClose()
          }, 400)
          return
        }

        if (status === 'FAILED' || status === 'ERROR') {
          setError(`识别失败: ${(extraction as any)?.error || '未知错误'}`)
          setStep('error')
          return
        }

        await new Promise((resolve) => setTimeout(resolve, 1000))
      } catch {
        setError('获取识别结果失败，请重试')
        setStep('error')
        return
      }
    }

    setError('识别超时，请重试')
    setStep('error')
  }

  const handleImageSelect = (capture?: boolean) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.multiple = true
    if (capture) input.capture = 'environment'

    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files
      if (files && files.length > 0) handleFileSelect(files)
    }

    input.click()
  }

  const handleClipboardImageSelect = async () => {
    setClipboardError(null)

    if (typeof navigator === 'undefined' || !navigator.clipboard || !navigator.clipboard.read) {
      setClipboardError('当前浏览器不支持剪切板图片读取，请改用拍照或相册上传。')
      return
    }

    try {
      const clipboardItems = await navigator.clipboard.read()
      const filesWithBlob: File[] = []
      for (let i = 0; i < clipboardItems.length; i += 1) {
        const item = clipboardItems[i]
        const imageType = item.types.find((type) => type.startsWith('image/'))
        if (!imageType) continue
        const blob = await item.getType(imageType)
        filesWithBlob.push(
          new File(
            [blob],
            `clipboard-${Date.now()}-${i}.${imageType.split('/')[1] || 'png'}`,
            { type: imageType }
          )
        )
      }

      if (filesWithBlob.length === 0) {
        setClipboardError('剪切板中没有图片，请先复制图片后再试。')
        return
      }

      await processFiles(filesWithBlob)
    } catch {
      setClipboardError('读取剪切板失败，请确认浏览器已授权剪切板读取权限。')
    }
  }

  const handleRetry = () => {
    setStep('select')
    setImagePreviews([])
    setUploadedImageIds([])
    setError(null)
    setClipboardError(null)
  }

  const handleClose = () => {
    onOpenChange(false)
    setTimeout(() => {
      setStep('select')
      setImagePreviews([])
      setUploadedImageIds([])
      setError(null)
      setClipboardError(null)
    }, 200)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>图片识别</DialogTitle>
          <DialogDescription>
            {step === 'select' && '上传图片后自动识别并回填题目信息'}
            {step === 'processing' && '正在识别，请稍候...'}
            {step === 'success' && '识别成功，正在回填...'}
            {step === 'error' && '识别失败，请重试'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {step === 'select' && (
            <>
              {imagePreviews.length > 0 && (
                <div className="grid grid-cols-2 gap-3">
                  {imagePreviews.map((preview, index) => (
                    <div key={preview.id} className="group relative overflow-hidden rounded-lg border">
                      <img src={preview.url} alt={`preview-${index + 1}`} className="h-36 w-full object-cover" />
                      <Button
                        type="button"
                        variant="destructive"
                        size="icon"
                        className="absolute right-2 top-2 h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100"
                        onClick={() => setImagePreviews((prev) => prev.filter((p) => p.id !== preview.id))}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="flex h-36 flex-col items-center justify-center rounded-lg border-2 border-dashed text-muted-foreground hover:bg-muted/50"
                    onClick={() => handleImageSelect(false)}
                  >
                    <Plus className="mb-2 h-7 w-7" />添加更多
                  </button>
                </div>
              )}

              {!selectedModel && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />选择识别模型
                  </Label>
                  <Select value={activeModel} onValueChange={handleModelChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择模型" />
                    </SelectTrigger>
                    <SelectContent>
                      {AVAILABLE_MODELS.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex flex-col">
                            <span>{model.name}</span>
                            <span className="text-xs text-muted-foreground">{model.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="grid grid-cols-1 gap-3">
                <Button variant="outline" size="lg" onClick={() => handleImageSelect(true)}>
                  <Camera className="mr-2 h-5 w-5" />拍照识别
                </Button>
                <Button variant="outline" size="lg" onClick={() => handleImageSelect(false)}>
                  <ImageIcon className="mr-2 h-5 w-5" />从相册选择
                </Button>
                <Button variant="outline" size="lg" onClick={handleClipboardImageSelect}>
                  <Plus className="mr-2 h-5 w-5" />从剪切板识别
                </Button>
              </div>

              <p className="text-center text-xs text-muted-foreground">支持多张图片，建议上传清晰图像</p>
              {clipboardError && (
                <p className="text-center text-xs text-destructive">{clipboardError}</p>
              )}
            </>
          )}

          {step === 'processing' && (
            <div className="flex flex-col items-center gap-3 py-8">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">正在识别题目内容...</p>
              {uploadedImageIds.length > 0 && (
                <p className="text-xs text-muted-foreground">已上传 {uploadedImageIds.length} 张</p>
              )}
            </div>
          )}

          {step === 'success' && (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="rounded-full bg-green-100 p-3">
                <Check className="h-7 w-7 text-green-600" />
              </div>
              <p className="text-sm">识别成功</p>
            </div>
          )}

          {step === 'error' && (
            <div className="space-y-4">
              <div className="flex flex-col items-center gap-2 py-4">
                <div className="rounded-full bg-red-100 p-3">
                  <AlertCircle className="h-7 w-7 text-red-600" />
                </div>
                <p className="text-sm">{error || '识别失败，请重试'}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button onClick={handleRetry}>重新识别</Button>
                <Button variant="outline" onClick={handleClose}>关闭</Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
