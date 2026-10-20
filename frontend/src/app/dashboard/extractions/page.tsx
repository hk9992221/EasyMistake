'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { extractionsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LatexContent } from '@/components/latex-content'

const labels = { PENDING: '排队中', RUNNING: '识别中', DONE: '已完成', FAILED: '失败' }

export default function ExtractionsPage() {
  const client = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const tasks = useQuery({
    queryKey: ['extractions-history'],
    queryFn: () => extractionsApi.list({ pageSize: 50 }),
    refetchInterval: (query) => query.state.data?.items.some((item) => ['PENDING', 'RUNNING'].includes(item.status)) ? 2000 : false,
  })
  const drafts = useQuery({
    queryKey: ['extraction-drafts', selectedId],
    queryFn: () => extractionsApi.getDraftQuestions(selectedId!),
    enabled: !!selectedId,
  })
  const retry = useMutation({
    mutationFn: extractionsApi.retry,
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['extractions-history'] }) },
    onError: (err: Error) => setError(err.message),
  })
  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold">识别记录</h1><p className="text-sm text-muted-foreground">最近 50 次任务；关闭录入窗口后仍可在这里查看结果。</p></div>
        <Link href="/dashboard/extract"><Button>录入试题</Button></Link>
      </div>
      {(error || tasks.isError || drafts.isError) && <p role="alert" className="text-destructive">{error || '加载失败，请稍后重试。'}</p>}
      {tasks.isLoading && <p>加载中...</p>}
      {tasks.data?.items.length === 0 && <p>暂无识别记录。</p>}
      {tasks.data?.items.map((task) => (
        <Card key={task.id}>
          <CardHeader><CardTitle className="text-base">{new Date(task.created_at).toLocaleString()} · {labels[task.status]}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {task.error && <p className="text-sm text-destructive">{task.error}</p>}
            {task.status === 'FAILED' && <Button disabled={retry.isPending} onClick={() => retry.mutate(task.id)}>重新识别</Button>}
            {task.status === 'DONE' && <Button variant="outline" onClick={() => setSelectedId(selectedId === task.id ? null : task.id)}>查看结果</Button>}
            {selectedId === task.id && drafts.isLoading && <p>加载结果中...</p>}
            {selectedId === task.id && drafts.data?.questions.map((question, index) => (
              <div key={index} className="space-y-2 rounded border p-4">
                <LatexContent text={[question.number, question.problem, question.choices, question.appendix].filter(Boolean).join('\n')} />
                <Button variant="outline" onClick={async () => {
                  try { await navigator.clipboard.writeText([question.problem, question.choices, question.appendix].filter(Boolean).join('\n')); setError('') }
                  catch { setError('复制失败，请手动选择题目文本。') }
                }}>复制题目</Button>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
