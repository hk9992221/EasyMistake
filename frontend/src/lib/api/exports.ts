/**
 * 导出相关 API
 */

import { apiClient } from './client'
import { Export, PaginatedResponse, PaginationParams } from '@/types/models'

export const exportsApi = {
  /**
   * 创建导出任务
   */
  create: async (data: { paper_set_id: string; format: 'MARKDOWN_ZIP' | 'LATEX_ZIP' | 'PDF' }) => {
    const response = await apiClient.post<Export>('/exports', data)
    return response.data
  },

  /**
   * 获取导出任务列表
   */
  list: async (params: PaginationParams = {}) => {
    const query = new URLSearchParams()
    const page = params.page || 1
    const pageSize = params.pageSize || params.page_size || 20
    query.append('skip', String((page - 1) * pageSize))
    query.append('limit', String(pageSize))

    const response = await apiClient.get<Export[]>(`/exports?${query}`)
    const items = response.data || []
    return {
      items,
      total: items.length,
      page,
      page_size: pageSize,
      total_pages: items.length > 0 ? 1 : 0,
    } as PaginatedResponse<Export>
  },

  /**
   * 获取导出任务详情
   */
  get: async (id: string) => {
    const response = await apiClient.get<Export>(`/exports/${id}`)
    return response.data
  },

  /**
   * 获取下载链接
   */
  getDownloadUrl: async (id: string) => {
    const response = await apiClient.post<{ download_url: string }>(`/exports/${id}/download-url`)
    return response.data.download_url
  },

  /**
   * 删除导出任务
   */
  delete: async (id: string) => {
    await apiClient.delete(`/exports/${id}`)
  },

  /**
   * 下载导出文件
   */
  download: async (id: string) => {
    const response = await apiClient.get<Blob>(`/exports/${id}/download`, {
      responseType: 'blob',
    })
    return response.data
  },
}
