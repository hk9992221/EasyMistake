/**
 * 答案相关 API
 */

import { apiClient } from './client'
import { Answer, AnswerImageItem } from '@/types/models'

export interface AnswerUpdateRequest {
  answer_type?: 'NONE' | 'TEXT' | 'LATEX' | 'IMAGE' | 'MIXED'
  answer_text?: string | null
  answer_latex?: string | null
  explanation_text?: string | null
  explanation_latex?: string | null
  content_json?: Record<string, any>
  images?: AnswerImageItem[]  // 支持多张图片
}

export const answersApi = {
  /**
   * 获取题目答案
   */
  getByQuestionId: async (questionId: string): Promise<Answer> => {
    const response = await apiClient.get<Answer>(`/questions/${questionId}/answer`)
    return response.data
  },

  /**
   * 创建或更新答案（使用 PUT）
   */
  upsert: async (questionId: string, data: AnswerUpdateRequest): Promise<Answer> => {
    const response = await apiClient.put<Answer>(`/questions/${questionId}/answer`, data)
    return response.data
  },

  /**
   * 创建答案（向后兼容）
   */
  create: async (questionId: string, data: AnswerUpdateRequest): Promise<Answer> => {
    return answersApi.upsert(questionId, data)
  },

  /**
   * 更新答案（向后兼容）
   */
  update: async (questionId: string, data: AnswerUpdateRequest): Promise<Answer> => {
    return answersApi.upsert(questionId, data)
  },

  /**
   * 删除答案
   */
  delete: async (questionId: string): Promise<void> => {
    await apiClient.delete(`/questions/${questionId}/answer`)
  },
}

/**
 * 答案图片管理 API（新增）
 */
export const answerImagesApi = {
  /**
   * 添加答案图片
   */
  addImage: async (questionId: string, imageId: string, orderIndex: number): Promise<void> => {
    await apiClient.post(`/questions/${questionId}/answer/images`, {
      image_id: imageId,
      order_index: orderIndex,
    })
  },

  /**
   * 删除答案图片
   */
  deleteImage: async (questionId: string, imageId: string): Promise<void> => {
    await apiClient.delete(`/questions/${questionId}/answer/images/${imageId}`)
  },

  /**
   * 调整答案图片顺序
   */
  reorderImages: async (questionId: string, images: { image_id: string; order_index: number }[]): Promise<void> => {
    await apiClient.patch(`/questions/${questionId}/answer/images/reorder`, { images })
  },
}
