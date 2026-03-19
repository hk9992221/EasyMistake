/**
 * 整卷/资料源相关 API
 */

import { apiClient } from './client'
import { Paper, PaginatedResponse, PaginationParams, Question } from '@/types/models'

export interface PaperFilters extends PaginationParams {
  subject?: string
  bookName?: string
  paperType?: string
  search?: string
}

export const papersApi = {
  /**
   * 获取整卷列表
   */
  list: async (filters: PaperFilters = {}) => {
    const params = new URLSearchParams()

    const page = filters.page || 1
    const pageSize = filters.pageSize || filters.page_size || 20
    params.append('skip', String((page - 1) * pageSize))
    params.append('limit', String(pageSize))
    if (filters.subject) params.append('subject', filters.subject)
    if (filters.paperType) params.append('kind', filters.paperType)
    if (filters.search) params.append('search', filters.search)

    const response = await apiClient.get<Paper[]>(`/papers?${params}`)
    const items = response.data || []
    return {
      items,
      total: items.length,
      page,
      page_size: pageSize,
      total_pages: items.length > 0 ? 1 : 0,
    } as PaginatedResponse<Paper>
  },

  /**
   * 获取单个整卷详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<Paper>(`/papers/${id}`)
    return response.data
  },

  /**
   * 通过二维码查找整卷
   */
  getByQrCode: async (qrCode: string) => {
    const response = await apiClient.get<Paper>(`/papers/by-qr/${encodeURIComponent(qrCode)}`)
    return response.data
  },

  /**
   * 创建整卷
   */
  create: async (data: Partial<Paper>) => {
    const response = await apiClient.post<Paper>('/papers', data)
    return response.data
  },

  /**
   * 更新整卷
   */
  update: async (id: string, data: Partial<Paper>) => {
    const response = await apiClient.patch<Paper>(`/papers/${id}`, data)
    return response.data
  },

  /**
   * 删除整卷
   */
  delete: async (id: string) => {
    await apiClient.delete(`/papers/${id}`)
  },

  /**
   * 获取整卷关联的题目
   */
  getQuestions: async (id: string) => {
    const response = await apiClient.get<Question[]>(`/papers/${id}/questions`)
    return response.data
  },
}
