/**
 * 图片相关 API
 */

import { apiClient } from './client'
import { Image, PaginatedResponse, PaginationParams } from '@/types/models'

export const imagesApi = {
  /**
   * 直接上传文件（推荐使用）
   */
  upload: async (file: File): Promise<Image> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post<Image>('/images/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * 获取上传 URL
   */
  getUploadUrl: async (filename: string, contentType: string) => {
    const response = await apiClient.post<{ upload_url: string; object_key: string }>('/images/upload-url', {
      filename,
      content_type: contentType,
    })
    return response.data
  },

  /**
   * 上传文件到 S3
   */
  uploadToS3: async (uploadUrl: string, file: File) => {
    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
      },
    })

    if (!response.ok) {
      throw new Error('上传失败')
    }

    return response
  },

  /**
   * 创建图片记录
   */
  create: async (objectKey: string, originalFilename: string) => {
    const response = await apiClient.post<Image>('/images', {
      object_key: objectKey,
      original_filename: originalFilename,
    })
    return response.data
  },

  /**
   * 获取图片列表
   */
  list: async (params: PaginationParams = {}) => {
    const query = new URLSearchParams()
    const page = params.page || 1
    const pageSize = params.pageSize || params.page_size || 20
    query.append('skip', String((page - 1) * pageSize))
    query.append('limit', String(pageSize))

    const response = await apiClient.get<Image[]>(`/images?${query}`)
    const items = response.data || []
    return {
      items,
      total: items.length,
      page,
      page_size: pageSize,
      total_pages: items.length > 0 ? 1 : 0,
    } as PaginatedResponse<Image>
  },

  /**
   * 获取单个图片详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<Image>(`/images/${id}`)
    return response.data
  },

  /**
   * 删除图片
   */
  delete: async (id: string) => {
    await apiClient.delete(`/images/${id}`)
  },

  /**
   * 获取图片预签名 URL
   */
  getPresignedUrl: async (id: string) => {
    return `/api/v1/images/${id}/file`
  },
}
