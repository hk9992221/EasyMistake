/**
 * 归档容器相关 API
 */

import { apiClient } from './client'
import { Submission, SubmissionItem, PaginatedResponse, PaginationParams } from '@/types/models'

export const submissionsApi = {
  /**
   * 获取归档容器列表
   */
  list: async (params: PaginationParams = {}) => {
    const query = new URLSearchParams()
    if (params.page) query.append('page', params.page.toString())
    if (params.pageSize) query.append('page_size', params.pageSize.toString())

    const response = await apiClient.get<PaginatedResponse<Submission>>(`/submissions?${query}`)
    return response.data
  },

  /**
   * 获取单个归档容器详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<Submission>(`/submissions/${id}`)
    return response.data
  },

  /**
   * 创建归档容器
   */
  create: async (data: Partial<Submission>) => {
    const response = await apiClient.post<Submission>('/submissions', data)
    return response.data
  },

  /**
   * 更新归档容器
   */
  update: async (id: string, data: Partial<Submission>) => {
    const response = await apiClient.put<Submission>(`/submissions/${id}`, data)
    return response.data
  },

  /**
   * 删除归档容器
   */
  delete: async (id: string) => {
    await apiClient.delete(`/submissions/${id}`)
  },

  /**
   * 获取归档容器的项目
   */
  getItems: async (id: string) => {
    const response = await apiClient.get<SubmissionItem[]>(`/submissions/${id}/items`)
    return response.data
  },

  /**
   * 添加题目到归档容器
   */
  addItem: async (id: string, questionId: string, data?: { userAnswer?: any; note?: string }) => {
    const response = await apiClient.post<SubmissionItem>(`/submissions/${id}/items`, {
      question_id: questionId,
      ...data,
    })
    return response.data
  },

  /**
   * 从归档容器移除题目
   */
  removeItem: async (id: string, itemId: string) => {
    await apiClient.delete(`/submissions/${id}/items/${itemId}`)
  },

  /**
   * 更新归档项目
   */
  updateItem: async (id: string, itemId: string, data: Partial<SubmissionItem>) => {
    const response = await apiClient.patch<SubmissionItem>(`/submissions/${id}/items/${itemId}`, data)
    return response.data
  },
}
