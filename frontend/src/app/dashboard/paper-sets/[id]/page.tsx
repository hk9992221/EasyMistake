'use client'

import Link from 'next/link'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Download,
  Edit2,
  File,
  FileArchive,
  History,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  X,
} from 'lucide-react'
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
import { LatexContent } from '@/components/latex-content'
import { apiClient } from '@/lib/api/client'
import { exportsApi, paperSetsApi } from '@/lib/api'
import { Export } from '@/types/models'
import { getQuestionTypeLabel } from '@/lib/question-type'

type ExportFormat = 'MARKDOWN_ZIP' | 'LATEX_ZIP' | 'PDF'

function normalizeStatus(status?: string) {
  return String(status || '').toUpperCase()
}

const PAPER_SET_DETAIL_RETURN_CONTEXT_KEY = 'paper_set_detail_return_context'

export default function PaperSetDetailPage() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const paperSetId = params.id as string

  const [isEditing, setIsEditing] = useState(false)
  const [editedTitle, setEditedTitle] = useState('')
  const [editedDescription, setEditedDescription] = useState('')
  const [showExportHistory, setShowExportHistory] = useState(false)
  const [exportStatus, setExportStatus] = useState<Record<string, string>>({})
  const [editScores, setEditScores] = useState<Record<string, string>>({})
  const [editSections, setEditSections] = useState<Record<string, string>>({})

  useEffect(() => {
    if (searchParams.get('exports') === 'true') setShowExportHistory(true)
  }, [searchParams])

  const { data: paperSet, isLoading: isLoadingPaperSet } = useQuery({
    queryKey: ['paper-set', paperSetId],
    queryFn: () => paperSetsApi.get(paperSetId),
  })

  const { data: previewData, isLoading: isLoadingPreview } = useQuery({
    queryKey: ['paper-set-preview', paperSetId],
    queryFn: () => paperSetsApi.preview(paperSetId),
  })

  const { data: paperSetExports = [], refetch: refetchExports } = useQuery({
    queryKey: ['exports', 'paper-set', paperSetId],
    queryFn: async () => {
      const response = await apiClient.get<Export[]>(`/exports/paper-sets/${paperSetId}`)
      return response.data
    },
    enabled: showExportHistory,
  })

  const updateMutation = useMutation({
    mutationFn: (data: { title?: string; description?: string }) => paperSetsApi.update(paperSetId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-set', paperSetId] })
      queryClient.invalidateQueries({ queryKey: ['paper-sets'] })
      setIsEditing(false)
    },
    onError: (error) => {
      console.error('update paper set failed', error)
      alert('更新组卷失败，请重试')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => paperSetsApi.delete(paperSetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-sets'] })
      router.push('/dashboard/paper-sets')
    },
  })

  const updateItemMutation = useMutation({
    mutationFn: ({ questionId, data }: { questionId: string; data: any }) =>
      paperSetsApi.updateItem(paperSetId, questionId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['paper-set-preview', paperSetId] }),
  })

  const deleteItemMutation = useMutation({
    mutationFn: (questionId: string) => paperSetsApi.removeItem(paperSetId, questionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['paper-set-preview', paperSetId] }),
  })

  const exportMutation = useMutation({
    mutationFn: async (format: ExportFormat) => {
      setExportStatus((prev) => ({ ...prev, [format]: 'PROCESSING' }))
      const task = await exportsApi.create({ paper_set_id: paperSetId, format })
      for (let i = 0; i < 60; i += 1) {
        const status = await exportsApi.get(task.id)
        const normalized = normalizeStatus(status.status)
        setExportStatus((prev) => ({ ...prev, [format]: normalized }))
        if (normalized === 'DONE' || normalized === 'COMPLETED') return task.id
        if (normalized === 'FAILED') throw new Error(status.error || '导出失败')
        await new Promise((resolve) => setTimeout(resolve, 1000))
      }
      throw new Error('导出超时')
    },
    onSuccess: async (exportId, format) => {
      setExportStatus((prev) => ({ ...prev, [format]: 'DONE' }))
      if (showExportHistory) await refetchExports()
      await handleDownloadExport(exportId, format)
    },
    onError: (error) => {
      console.error(error)
    },
  })

  const questions = previewData?.questions || []
  const totalScore = useMemo(
    () => questions.reduce((sum: number, q: any) => sum + Number(q.score || 0), 0),
    [questions]
  )

  const openQuestionDetail = (questionId: string, index: number) => {
    const context = {
      source: 'paper-set-detail',
      paperSetId,
      questionId,
      questionIndex: index,
    }
    sessionStorage.setItem(PAPER_SET_DETAIL_RETURN_CONTEXT_KEY, JSON.stringify(context))
    router.push(
      `/dashboard/questions/${questionId}?from_paper_set=1&paper_set_id=${paperSetId}&question_index=${index}`
    )
  }

  const handleDownloadExport = async (exportId: string, format: ExportFormat | string) => {
    const blob = await exportsApi.download(exportId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const extension = format === 'PDF' ? 'pdf' : format === 'LATEX_ZIP' ? 'tex.zip' : 'md.zip'
    a.download = `export_${exportId}.${extension}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }

  if (isLoadingPaperSet || isLoadingPreview) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">加载中...</div>
  }

  if (!paperSet || !previewData) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">组卷不存在</div>
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl p-8 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              {isEditing ? (
                <div className="flex items-center gap-2">
                  <Input value={editedTitle} onChange={(e) => setEditedTitle(e.target.value)} className="text-lg font-semibold" />
                  <Button size="icon" onClick={() => updateMutation.mutate({ title: editedTitle, description: editedDescription })}>
                    <Save className="h-4 w-4" />
                  </Button>
                  <Button size="icon" variant="ghost" onClick={() => setIsEditing(false)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold">{paperSet.title}</h1>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => {
                      setEditedTitle(paperSet.title || '')
                      setEditedDescription(paperSet.description || '')
                      setIsEditing(true)
                    }}
                  >
                    <Edit2 className="h-4 w-4" />
                  </Button>
                </div>
              )}
              {isEditing ? (
                <Input value={editedDescription} onChange={(e) => setEditedDescription(e.target.value)} />
              ) : (
                paperSet.description && <p className="text-muted-foreground">{paperSet.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setShowExportHistory((v) => !v)}>
              <History className="mr-2 h-4 w-4" />
              导出历史
            </Button>
            <Select onValueChange={(v) => exportMutation.mutate(v as ExportFormat)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="导出" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="MARKDOWN_ZIP">Markdown</SelectItem>
                <SelectItem value="LATEX_ZIP">LaTeX</SelectItem>
                <SelectItem value="PDF">PDF</SelectItem>
              </SelectContent>
            </Select>
            <Link href={`/dashboard/paper-sets/${paperSetId}/review`}>
              <Button variant="outline">批改页</Button>
            </Link>
            <Button variant="destructive" size="icon" onClick={() => deleteMutation.mutate()}>
              {deleteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{questions.length}</div><div className="text-sm text-muted-foreground">题目数</div></CardContent></Card>
          <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{totalScore}</div><div className="text-sm text-muted-foreground">总分</div></CardContent></Card>
          <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{paperSet.subject || '-'}</div><div className="text-sm text-muted-foreground">学科</div></CardContent></Card>
          <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{paperSet.output_format || '-'}</div><div className="text-sm text-muted-foreground">输出格式</div></CardContent></Card>
        </div>

        {showExportHistory && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>导出历史</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => refetchExports()}><RefreshCw className="mr-2 h-4 w-4" />刷新</Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {paperSetExports.length === 0 && <p className="text-sm text-muted-foreground">暂无导出记录</p>}
              {paperSetExports.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded border p-3">
                  <div className="flex items-center gap-3">
                    {item.format === 'PDF' ? <File className="h-5 w-5" /> : <FileArchive className="h-5 w-5" />}
                    <div>
                      <div className="font-medium">{item.format}</div>
                      <div className="text-xs text-muted-foreground">{item.created_at ? new Date(item.created_at).toLocaleString() : '-'}</div>
                    </div>
                    <Badge variant="outline">{normalizeStatus(item.status)}</Badge>
                  </div>
                  {(normalizeStatus(item.status) === 'DONE' || normalizeStatus(item.status) === 'COMPLETED') && item.object_key && (
                    <Button size="sm" onClick={() => handleDownloadExport(item.id, item.format)}><Download className="mr-2 h-4 w-4" />下载</Button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        <div className="space-y-4">
          {questions.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center">
                <p className="text-muted-foreground">组卷暂无题目</p>
                <Button className="mt-4" onClick={() => router.push('/dashboard/paper-sets')}>
                  <Plus className="mr-2 h-4 w-4" />添加题目
                </Button>
              </CardContent>
            </Card>
          ) : (
            questions.map((question: any, index: number) => (
              <Card key={question.id}>
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">#{question.order_index || index + 1}</Badge>
                        <Badge>{getQuestionTypeLabel(question.type)}</Badge>
                        {question.score !== undefined && <Badge variant="outline">{question.score} 分</Badge>}
                      </div>
                      <CardTitle className="text-base">
                        <button
                          type="button"
                          className="w-full text-left hover:underline"
                          onClick={() => openQuestionDetail(question.id, index)}
                        >
                          <LatexContent text={question.stem_latex || question.stem_text || ''} className="prose prose-sm max-w-none" />
                        </button>
                      </CardTitle>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        placeholder="分值"
                        defaultValue={question.score}
                        onChange={(e) => setEditScores((prev) => ({ ...prev, [question.id]: e.target.value }))}
                        className="w-24"
                      />
                      <Input
                        placeholder="分组"
                        defaultValue={question.section_title || ''}
                        onChange={(e) => setEditSections((prev) => ({ ...prev, [question.id]: e.target.value }))}
                        className="w-32"
                      />
                      <Button
                        size="icon"
                        variant="outline"
                        onClick={() =>
                          updateItemMutation.mutate({
                            questionId: question.id,
                            data: {
                              score: editScores[question.id] ? Number(editScores[question.id]) : undefined,
                              section_title: editSections[question.id],
                            },
                          })
                        }
                      >
                        <Save className="h-4 w-4" />
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => deleteItemMutation.mutate(question.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
