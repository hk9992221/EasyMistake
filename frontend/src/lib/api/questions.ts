/**
 * 题目相关 API
 */

import { apiClient } from './client'
import { Question, PaginatedResponse, QuestionFilters } from '@/types/models'

export const questionsApi = {
  /**
   * 获取题目列表
   */
  list: async (filters: QuestionFilters = {}) => {
    const params = new URLSearchParams()

    if (filters.page) params.append('page', filters.page.toString())
    if (filters.pageSize) params.append('page_size', filters.pageSize.toString())
    if (filters.subject) params.append('subject', filters.subject)
    if (filters.book_name) params.append('book_name', filters.book_name)
    if (filters.chapter_name) params.append('chapter_name', filters.chapter_name)
    if (filters.page_no) params.append('page_no', filters.page_no.toString())
    if (filters.question_no) params.append('question_no', filters.question_no)
    if (filters.type) params.append('type', filters.type)
    if (filters.difficulty) params.append('difficulty', filters.difficulty)
    if (filters.knowledge_point_q) params.append('knowledge_point_q', filters.knowledge_point_q)
    if (filters.q) params.append('q', filters.q)
    if (filters.start_date) params.append('start_date', filters.start_date)
    if (filters.end_date) params.append('end_date', filters.end_date)
    if (filters.sortBy) params.append('sort_by', filters.sortBy)
    if (filters.sortOrder) params.append('sort_order', filters.sortOrder)

    if (filters.tags_json) {
      filters.tags_json.forEach((tag) => params.append('tags_json', tag))
    }

    const response = await apiClient.get<PaginatedResponse<Question>>(`/questions?${params}`)
    return response.data
  },

  /**
   * 获取单个题目详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<Question>(`/questions/${id}`)
    return response.data
  },

  /**
   * 创建题目
   */
  create: async (data: Partial<Question>) => {
    const response = await apiClient.post<Question>('/questions', data)
    return response.data
  },

  /**
   * 更新题目
   */
  update: async (id: string, data: Partial<Question>) => {
    const response = await apiClient.patch<Question>(`/questions/${id}`, data)
    return response.data
  },

  /**
   * 删除题目（软删除）
   */
  delete: async (id: string) => {
    await apiClient.delete(`/questions/${id}`)
  },

  /**
   * 批量删除题目
   */
  bulkDelete: async (ids: string[]) => {
    await apiClient.post('/questions/bulk-delete', { question_ids: ids })
  },

  /**
   * 获取用户常用tag
   */
  getCommonTags: async (limit: number = 4) => {
    const response = await apiClient.get<{ tags: string[] }>(`/questions/user/common-tags?limit=${limit}`)
    return response.data.tags
  },

  /**
   * 为题目添加图片
   */
  addImage: async (questionId: string, imageId: string) => {
    const response = await apiClient.post<{ message: string }>(`/questions/${questionId}/images?image_id=${imageId}`)
    return response.data
  },

  /**
   * 从题干移除图片
   */
  removeImage: async (questionId: string, imageId: string) => {
    await apiClient.delete(`/questions/${questionId}/images/${imageId}`)
  },

  /**
   * 重新排列题干图片顺序
   */
  reorderImages: async (questionId: string, imageIds: string[]) => {
    const response = await apiClient.patch<{ message: string }>(`/questions/${questionId}/images/reorder`, imageIds)
    return response.data
  },
}
