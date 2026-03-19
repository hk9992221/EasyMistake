/**
 * 应用常量定义
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''
export const API_PREFIX = '/api/v1'

export const QUESTION_TYPES = [
  { value: 'multiple_choice', label: '选择题' },
  { value: 'fill_blank', label: '填空题' },
  { value: 'short_answer', label: '简答题' },
  { value: 'essay', label: '论述题' },
  { value: 'calculation', label: '计算题' },
] as const

export const DIFFICULTY_LEVELS = [
  { value: 'easy', label: '容易' },
  { value: 'medium', label: '中等' },
  { value: 'hard', label: '困难' },
] as const

export const SUBJECTS = [
  { value: 'math', label: '数学' },
  { value: 'physics', label: '物理' },
  { value: 'chemistry', label: '化学' },
  { value: 'biology', label: '生物' },
  { value: 'chinese', label: '语文' },
  { value: 'english', label: '英语' },
  { value: 'history', label: '历史' },
  { value: 'geography', label: '地理' },
  { value: 'politics', label: '政治' },
] as const

export const PAPER_TYPES = [
  { value: 'exam_paper', label: '试卷' },
  { value: 'textbook', label: '教材' },
  { value: 'workbook', label: '练习册' },
  { value: 'other', label: '其他' },
] as const

export const EXTRACTION_STATUS = [
  { value: 'pending', label: '等待中' },
  { value: 'processing', label: '处理中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
] as const

export const EXPORT_STATUS = [
  { value: 'pending', label: '等待中' },
  { value: 'processing', label: '处理中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
] as const

export const EXPORT_FORMATS = [
  { value: 'markdown', label: 'Markdown' },
  { value: 'latex', label: 'LaTeX' },
  { value: 'pdf', label: 'PDF' },
] as const

export const USER_ROLES = [
  { value: 'USER', label: '普通用户' },
  { value: 'ADMIN', label: '管理员' },
] as const

export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100
