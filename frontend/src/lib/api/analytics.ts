import { apiClient } from './client'
import { AnalyticsOverview, ErrorTagStatItem } from '@/types/models'

export const analyticsApi = {
  overview: async () => {
    const response = await apiClient.get<AnalyticsOverview>('/analytics/overview')
    return response.data
  },

  errorTags: async (top: number = 10) => {
    const response = await apiClient.get<{ items: ErrorTagStatItem[] }>(`/analytics/error-tags?top=${top}`)
    return response.data
  },
}
