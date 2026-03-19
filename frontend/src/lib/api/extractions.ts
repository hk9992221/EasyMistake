/**
 * 识别任务相关 API
 */

import { apiClient } from './client'
import { Extraction, DraftQuestion, Question, PaginatedResponse, PaginationParams } from '@/types/models'

export const extractionsApi = {
  /**
   * 创建识别任务
   */
  create: async (imageIds: string[], modelName?: string) => {
    const response = await apiClient.post<Extraction>('/extractions', {
      image_ids: imageIds,
      model_name: modelName || 'qwen3-vl-flash',
    })
    return { extraction_id: response.data.id }
  },

  /**
   * 获取识别任务列表
   */
  list: async (params: PaginationParams = {}) => {
    const query = new URLSearchParams()
    const page = params.page || 1
    const pageSize = params.pageSize || params.page_size || 20
    query.append('skip', String((page - 1) * pageSize))
    query.append('limit', String(pageSize))

    const response = await apiClient.get<Extraction[]>(`/extractions?${query}`)
    const items = response.data || []
    return {
      items,
      total: items.length,
      page,
      page_size: pageSize,
      total_pages: items.length > 0 ? 1 : 0,
    } as PaginatedResponse<Extraction>
  },

  /**
   * 获取识别任务详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<Extraction>(`/extractions/${id}`)
    return response.data
  },

  /**
   * 获取识别结果草稿
   */
  getDraftQuestions: async (id: string) => {
    const response = await apiClient.get<{ questions: DraftQuestion[] }>(`/extractions/${id}/draft-questions`)
    return response.data
  },

  /**
   * 将草稿题目正式入库
   */
  confirmQuestions: async (id: string, questions: DraftQuestion[]) => {
    const response = await apiClient.post<{ questions: Question[] }>(
      `/extractions/${id}/questions`,
      { questions }
    )
    return response.data
  },

  /**
   * 删除识别任务
   */
  delete: async (_id: string) => {
    throw new Error('当前后端未提供删除识别任务接口')
  },

  /**
   * 重新执行识别任务
   */
  retry: async (id: string) => {
    const response = await apiClient.post<Extraction>(`/extractions/${id}/retry`)
    return response.data
  },
}
