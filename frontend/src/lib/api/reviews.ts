import { apiClient } from './client'
import { ReviewQueueResponse } from '@/types/models'

export interface ReviewCompletePayload {
  result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED'
  duration_sec?: number
  error_tags?: string[]
  note?: string
}

export const reviewsApi = {
  getToday: async () => {
    const response = await apiClient.get<ReviewQueueResponse>('/reviews/today')
    return response.data
  },

  getQueue: async () => {
    const response = await apiClient.get<ReviewQueueResponse>('/reviews/queue')
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
