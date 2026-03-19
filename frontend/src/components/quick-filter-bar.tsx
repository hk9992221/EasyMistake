'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, X, ChevronDown, ChevronUp } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { questionsApi } from '@/lib/api'

export interface QuickFilterData {
  searchQuery: string
  questionNo: string
  subject: string
  selectedTags: string[]
  knowledgePointRegex: string
  difficulty: string
  type: string
  bookName: string
  chapterName: string
  masteryLevel: string
  customMastery: string
  startDate: string
  endDate: string
}

interface QuickFilterBarProps {
  filters: QuickFilterData
  onChange: (filters: QuickFilterData) => void
  compact?: boolean
}

export function QuickFilterBar({ filters, onChange, compact = false }: QuickFilterBarProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [manualLogicMode, setManualLogicMode] = useState(false)

  const { data: commonTags = [] } = useQuery({
    queryKey: ['common-tags'],
    queryFn: () => questionsApi.getCommonTags(6),
  })

  const toggleTag = (tag: string) => {
    const newTags = filters.selectedTags.includes(tag)
      ? filters.selectedTags.filter((t) => t !== tag)
      : [...filters.selectedTags, tag]
    onChange({ ...filters, selectedTags: newTags })
  }

  const updateField = (field: keyof QuickFilterData, value: string) => {
    onChange({ ...filters, [field]: value })
  }

  const resetFilters = () => {
    onChange({
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
  }

  const hasActiveFilters =
    !!filters.searchQuery ||
    !!filters.questionNo ||
    !!filters.subject ||
    filters.selectedTags.length > 0 ||
    !!filters.knowledgePointRegex ||
    (filters.difficulty && filters.difficulty !== 'all') ||
    (filters.type && filters.type !== 'all') ||
    !!filters.bookName ||
    !!filters.chapterName ||
    filters.masteryLevel !== 'all' ||
    !!filters.startDate ||
    !!filters.endDate

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={manualLogicMode ? "搜索题目内容（可写 AND / OR）" : "搜索题目内容..."}
              value={filters.searchQuery}
              onChange={(e) => updateField('searchQuery', e.target.value)}
              className="pl-9"
            />
          </div>
          <Button
            variant={manualLogicMode ? 'default' : 'outline'}
            size="sm"
            onClick={() => setManualLogicMode((v) => !v)}
          >
            手写 AND/OR
          </Button>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              <X className="mr-2 h-4 w-4" />
              清空筛选
            </Button>
          )}
          {!compact && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAdvanced((v) => !v)}
            >
              高级筛选
              {showAdvanced ? (
                <ChevronUp className="ml-2 h-4 w-4" />
              ) : (
                <ChevronDown className="ml-2 h-4 w-4" />
              )}
            </Button>
          )}
        </div>

        {manualLogicMode && (
          <div className="text-xs text-muted-foreground">
            逻辑示例：`张宇 AND 高数`，`张宇 OR 李永乐`，不写运算符时默认按空格做 AND。
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="题号"
            value={filters.questionNo}
            onChange={(e) => updateField('questionNo', e.target.value)}
            className="w-32"
          />

          <Input
            placeholder="学科"
            value={filters.subject}
            onChange={(e) => updateField('subject', e.target.value)}
            className="w-32"
          />

          <Select value={filters.difficulty || 'all'} onValueChange={(v) => updateField('difficulty', v)}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="难度" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部难度</SelectItem>
              <SelectItem value="EASY">简单</SelectItem>
              <SelectItem value="MEDIUM">中等</SelectItem>
              <SelectItem value="HARD">困难</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filters.type || 'all'} onValueChange={(v) => updateField('type', v)}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="题型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部题型</SelectItem>
              <SelectItem value="MCQ">选择题</SelectItem>
              <SelectItem value="FILL_BLANK">填空题</SelectItem>
              <SelectItem value="SHORT_ANSWER">简答题</SelectItem>
              <SelectItem value="COMPUTATION">计算题</SelectItem>
              <SelectItem value="PROOF">证明题</SelectItem>
            </SelectContent>
          </Select>

          {commonTags.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">常用:</span>
              <div className="flex flex-wrap gap-1">
                {commonTags.slice(0, 4).map((tag) => (
                  <Badge
                    key={tag}
                    variant={filters.selectedTags.includes(tag) ? 'default' : 'outline'}
                    className="cursor-pointer text-xs"
                    onClick={() => toggleTag(tag)}
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {filters.selectedTags.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">已选:</span>
              <div className="flex flex-wrap gap-1">
                {filters.selectedTags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="gap-1 text-xs">
                    {tag}
                    <X className="h-3 w-3 cursor-pointer" onClick={() => toggleTag(tag)} />
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        {!compact && showAdvanced && (
          <div className="space-y-3 border-t pt-3">
            <div className="flex flex-wrap gap-3">
              <Input
                placeholder={manualLogicMode ? "教材/来源（支持 AND / OR）" : "教材/来源"}
                value={filters.bookName}
                onChange={(e) => updateField('bookName', e.target.value)}
                className="w-40"
              />

              <Input
                placeholder={manualLogicMode ? "章节（支持 AND / OR）" : "章节"}
                value={filters.chapterName}
                onChange={(e) => updateField('chapterName', e.target.value)}
                className="w-32"
              />

              <Input
                placeholder={manualLogicMode ? "知识点（支持 AND / OR）" : "知识点"}
                value={filters.knowledgePointRegex}
                onChange={(e) => updateField('knowledgePointRegex', e.target.value)}
                className="w-40"
              />

              <Select value={filters.masteryLevel || 'all'} onValueChange={(v) => updateField('masteryLevel', v)}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="掌握度" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="low">未掌握 (≤60%)</SelectItem>
                  <SelectItem value="medium">部分掌握 (≤80%)</SelectItem>
                  <SelectItem value="high">已掌握 ({'>'}80%)</SelectItem>
                  <SelectItem value="custom">自定义</SelectItem>
                </SelectContent>
              </Select>

              {filters.masteryLevel === 'custom' && (
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    placeholder="阈值"
                    min="0"
                    max="100"
                    value={filters.customMastery}
                    onChange={(e) => updateField('customMastery', e.target.value)}
                    className="w-20"
                  />
                  <span className="text-sm text-muted-foreground">%以下</span>
                </div>
              )}

              <Input
                type="date"
                value={filters.startDate}
                onChange={(e) => updateField('startDate', e.target.value)}
                className="w-36"
              />
              <span className="text-sm text-muted-foreground">至</span>
              <Input
                type="date"
                value={filters.endDate}
                onChange={(e) => updateField('endDate', e.target.value)}
                className="w-36"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
