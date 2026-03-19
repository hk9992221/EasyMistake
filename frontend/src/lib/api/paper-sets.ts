/**
 * 组卷相关 API
 */

import { apiClient } from './client'
import { PaperSet, PaperSetItem, PaginatedResponse, PaginationParams } from '@/types/models'

export interface PaperSetListFilters extends PaginationParams {
  search?: string
  name_regex?: string
  start_date?: string
  end_date?: string
}

export const paperSetsApi = {
  /**
   * 获取组卷列表
   */
  list: async (params: PaperSetListFilters = {}) => {
    const query = new URLSearchParams()
    if (params.page) query.append('page', params.page.toString())
    if (params.pageSize) query.append('page_size', params.pageSize.toString())
    if (params.page_size) query.append('page_size', params.page_size.toString())
    if (params.search) query.append('search', params.search)
    if (params.name_regex) query.append('name_regex', params.name_regex)
    if (params.start_date) query.append('start_date', params.start_date)
    if (params.end_date) query.append('end_date', params.end_date)

    const response = await apiClient.get<PaginatedResponse<PaperSet>>(`/paper-sets?${query}`)
    return response.data
  },

  /**
   * 获取单个组卷详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<PaperSet>(`/paper-sets/${id}`)
    return response.data
  },

  /**
   * 创建组卷
   */
  create: async (data: Partial<PaperSet>) => {
    const response = await apiClient.post<PaperSet>('/paper-sets', data)
    return response.data
  },

  /**
   * 更新组卷
   */
  update: async (id: string, data: Partial<PaperSet>) => {
    const response = await apiClient.patch<PaperSet>(`/paper-sets/${id}`, data)
    return response.data
  },

  /**
   * 删除组卷
   */
  delete: async (id: string) => {
    await apiClient.delete(`/paper-sets/${id}`)
  },

  /**
   * 获取组卷的项目
   */
  getItems: async (id: string) => {
    const response = await apiClient.get<PaperSetItem[]>(`/paper-sets/${id}/items`)
    return response.data
  },

  /**
   * 添加题目到组卷
   */
  addItem: async (id: string, questionId: string, data?: Partial<PaperSetItem>) => {
    const response = await apiClient.put<PaperSetItem>(`/paper-sets/${id}/items/${questionId}`, {
      question_id: questionId,
      order_index: (data as any)?.order_index ?? 0,
      section_title: (data as any)?.section_title,
      score: (data as any)?.score,
    })
    return response.data
  },

  /**
   * 从组卷移除题目
   */
  removeItem: async (id: string, questionId: string) => {
    await apiClient.delete(`/paper-sets/${id}/items/${questionId}`)
  },

  /**
   * 更新组卷项目
   */
  updateItem: async (id: string, questionId: string, data: Partial<PaperSetItem>) => {
    const response = await apiClient.patch<PaperSetItem>(`/paper-sets/${id}/items/${questionId}`, data)
    return response.data
  },

  /**
   * 获取组卷预览
   */
  preview: async (id: string) => {
    const response = await apiClient.get<any>(`/paper-sets/${id}/preview`)
    return response.data
  },

  /**
   * 批量添加题目到组卷
   */
  batchAddItems: async (id: string, items: Array<{ question_id: string; order_index: number; section_title?: string; score?: number }>) => {
    const response = await apiClient.post<PaperSetItem[]>(`/paper-sets/${id}/items/batch`, { items })
    return response.data
  },
}
