import { apiClient } from './client'
import { ReviewQueueResponse } from '@/types/models'

export interface ReviewCompletePayload {
  result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED'
  duration_sec?: number
  error_tags?: string[]
  note?: string
}

export interface ReviewQueueParams {
  page?: number
  page_size?: number
  subject?: string
  include_details?: boolean
}

export const reviewsApi = {
  getToday: async (params?: ReviewQueueParams) => {
    const response = await apiClient.get<ReviewQueueResponse>('/reviews/today', { params })
    return response.data
  },

  getQueue: async (params?: ReviewQueueParams) => {
    const response = await apiClient.get<ReviewQueueResponse>('/reviews/queue', { params })
    return response.data
  },

  generateDailyPaperSet: async (subject?: string) => {
    const response = await apiClient.post<{
      paper_set_id: string
      title: string
      item_count: number
      reused: boolean
    }>('/reviews/daily-paper-set', { subject })
    return response.data
  },

  complete: async (questionId: string, payload: ReviewCompletePayload) => {
    const response = await apiClient.post<{ attempt_id: string }>(`/reviews/${questionId}/complete`, payload)
    return response.data
  },

  recalculate: async () => {
    const response = await apiClient.post<{ updated: number }>('/reviews/recalculate')
    return response.data
  },
}
