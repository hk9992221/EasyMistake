import { apiClient } from './client'
import { PaginatedResponse, QuestionProgress } from '@/types/models'

export interface QuestionProgressFilters {
  page?: number
  pageSize?: number
  questionId?: string
  dueOnly?: boolean
}

export const questionProgressApi = {
  list: async (filters: QuestionProgressFilters = {}) => {
    const params = new URLSearchParams()
    params.append('page', String(filters.page || 1))
    params.append('page_size', String(filters.pageSize || 20))
    if (filters.questionId) params.append('question_id', filters.questionId)
    if (filters.dueOnly) params.append('due_only', 'true')
    const response = await apiClient.get<PaginatedResponse<QuestionProgress>>(`/question-progress/?${params}`)
    return response.data
  },

  create: async (questionId: string) => {
    const response = await apiClient.post<QuestionProgress>('/question-progress/', { question_id: questionId })
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<QuestionProgress>(`/question-progress/${id}`)
    return response.data
  },

  update: async (id: string, data: Partial<QuestionProgress>) => {
    const response = await apiClient.patch<QuestionProgress>(`/question-progress/${id}`, data)
    return response.data
  },
}
