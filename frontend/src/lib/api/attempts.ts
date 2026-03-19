/**
 * 做题记录相关 API
 */

import { apiClient } from './client'
import { Attempt, PaginatedResponse, PaginationParams } from '@/types/models'

export interface AttemptFilters extends PaginationParams {
  questionId?: string
  attemptType?: 'practice' | 'exam'
  isCorrect?: boolean
}

export const attemptsApi = {
  /**
   * 获取做题记录列表
   */
  list: async (filters: AttemptFilters = {}) => {
    const params = new URLSearchParams()

    if (filters.page) params.append('page', filters.page.toString())
    if (filters.pageSize) params.append('page_size', filters.pageSize.toString())
    if (filters.questionId) params.append('question_id', filters.questionId)
    if (filters.attemptType) params.append('source', filters.attemptType)
    if (filters.isCorrect !== undefined) params.append('result', filters.isCorrect ? 'CORRECT' : 'WRONG')

    const response = await apiClient.get<Attempt[]>(`/question-attempts?${params}`)
    const page = filters.page || 1
    const pageSize = filters.pageSize || 20
    return response.data
      ? {
          items: response.data,
          total: response.data.length,
          page,
          page_size: pageSize,
          total_pages: 1,
        } as PaginatedResponse<Attempt>
      : { items: [], total: 0, page, page_size: pageSize, total_pages: 0 }
  },

  /**
   * 获取单个做题记录详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<Attempt>(`/question-attempts/${id}`)
    return response.data
  },

  /**
   * 创建做题记录
   */
  create: async (data: Partial<Attempt> & { question_id?: string; result?: Attempt['result'] }) => {
    const response = await apiClient.post<Attempt>('/question-attempts', data)
    return response.data
  },

  /**
   * 获取题目的做题记录
   */
  getByQuestionId: async (questionId: string) => {
    const response = await apiClient.get<Attempt[]>(`/questions/${questionId}/attempts`)
    return response.data
  },

  setErrorTags: async (attemptId: string, tags: string[]) => {
    const response = await apiClient.post<Attempt>(`/question-attempts/${attemptId}/error-tags`, tags)
    return response.data
  },

  /**
   * 获取做题统计
   */
  getStats: async () => {
    const response = await apiClient.get<{
      total_attempts: number
      total_wrong_questions: number
      unmastered_wrong_questions: number
    }>('/attempts/stats')
    return response.data
  },
}
