'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RotateCcw, Trash2 } from 'lucide-react'
import { questionsApi } from '@/lib/api'
import { invalidateLearning } from '@/lib/api/invalidate-learning'
import { useToast } from '@/lib/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { LatexContent } from '@/components/latex-content'

export default function TrashPage() {
  const [page, setPage] = useState(1)
  const client = useQueryClient()
  const { toast } = useToast()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['questions-trash', page],
    queryFn: () => questionsApi.trash(page),
  })
  const restore = useMutation({
    mutationFn: questionsApi.restore,
    onSuccess: () => {
      if (data?.items.length === 1 && page > 1) setPage(page - 1)
      void client.invalidateQueries({ queryKey: ['questions-trash'] })
      invalidateLearning(client)
      toast({ title: '已恢复', description: '题目、答案和做题记录已保留，可在题库中查看。' })
    },
    onError: (error: any) => toast({ title: '恢复失败', description: error?.message || '请稍后重试', variant: 'destructive' }),
  })
  const pages = data?.total_pages || 1

  return <div className="mx-auto max-w-5xl space-y-6 p-8">
    <div>
      <h1 className="flex items-center gap-2 text-2xl font-bold"><Trash2 className="h-6 w-6" />回收站</h1>
      <p className="mt-2 text-sm text-muted-foreground">恢复误删题目，保留原有答案、图片和复习记录。</p>
    </div>
    {isLoading && <p role="status">正在加载…</p>}
    {isError && <Button variant="outline" onClick={() => refetch()}>加载失败，点击重试</Button>}
    {!isLoading && !isError && data?.items.length === 0 && <p className="rounded-lg border p-8 text-center text-muted-foreground">暂无已删除的题目</p>}
    {data?.items.map((question) => <Card key={question.id}><CardContent className="flex items-start justify-between gap-6 p-5">
      <div className="min-w-0 space-y-2">
        <p className="text-sm text-muted-foreground">{[question.subject, question.book_name, question.question_no].filter(Boolean).join(' · ') || '未分类题目'}</p>
        <LatexContent text={question.stem_text || question.stem_latex || '图片题目'} className="line-clamp-4 whitespace-pre-wrap" />
      </div>
      <Button variant="outline" className="shrink-0" disabled={restore.isPending} onClick={() => restore.mutate(question.id)}>
        <RotateCcw className="mr-2 h-4 w-4" />恢复
      </Button>
    </CardContent></Card>)}
    {data && data.total > 0 && <div className="flex items-center justify-between">
      <p className="text-sm text-muted-foreground">共 {data.total} 道 · 第 {page} / {pages} 页</p>
      <div className="flex gap-2">
        <Button variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</Button>
        <Button variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>下一页</Button>
      </div>
    </div>}
  </div>
}
