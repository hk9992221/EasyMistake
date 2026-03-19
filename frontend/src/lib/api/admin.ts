/**
 * 管理员相关 API
 */

import { apiClient } from './client'
import { User, Invite, ApiCallLog, PaginatedResponse, PaginationParams } from '@/types/models'

export interface UserFilters extends PaginationParams {
  email?: string
  username?: string
  role?: 'USER' | 'ADMIN'
  search?: string
}

export interface InviteFilters extends PaginationParams {
  isActive?: boolean
}

export interface LogFilters extends PaginationParams {
  userId?: string
  purpose?: string
  provider?: string
  startDay?: string
  endDay?: string
  search?: string
}

export const adminApi = {
  // ==================== 用户管理 ====================
  /**
   * 获取用户列表
   */
  listUsers: async (filters: UserFilters = {}) => {
    const params = new URLSearchParams()

    const page = filters.page || 1
    const pageSize = filters.pageSize || filters.page_size || 20
    params.append('page', page.toString())
    params.append('page_size', pageSize.toString())
    if (filters.search) params.append('search', filters.search)
    if (filters.role) params.append('role', filters.role)

    const response = await apiClient.get<PaginatedResponse<User>>(`/admin/users?${params}`)
    const data = response.data as any
    const total = Number(data?.total || 0)
    return {
      ...data,
      page,
      page_size: pageSize,
      total_pages: Math.ceil(total / pageSize) || 1,
    } as PaginatedResponse<User>
  },

  /**
   * 获取用户详情
   */
  getUser: async (id: string) => {
    const response = await apiClient.get<User>(`/admin/users/${id}`)
    return response.data
  },

  /**
   * 创建用户
   */
  createUser: async (data: { email: string; password: string; role?: 'USER' | 'ADMIN' }) => {
    const response = await apiClient.post<User>('/admin/users', data)
    return response.data
  },

  /**
   * 更新用户角色
   */
  updateUserRole: async (id: string, role: 'USER' | 'ADMIN') => {
    const response = await apiClient.patch<User>(`/admin/users/${id}/role`, { role })
    return response.data
  },

  /**
   * 删除用户
   */
  deleteUser: async (id: string) => {
    await apiClient.delete(`/admin/users/${id}`)
  },

  // ==================== 邀请码管理 ====================
  /**
   * 获取邀请码列表
   */
  listInvites: async (filters: InviteFilters = {}) => {
    const params = new URLSearchParams()

    const page = filters.page || 1
    const pageSize = filters.pageSize || filters.page_size || 20
    params.append('skip', String((page - 1) * pageSize))
    params.append('limit', String(pageSize))

    const response = await apiClient.get<Invite[]>(`/auth/invites?${params}`)
    const items = response.data || []
    return {
      items,
      total: items.length,
      page,
      page_size: pageSize,
      total_pages: items.length > 0 ? 1 : 0,
    } as PaginatedResponse<Invite>
  },

  /**
   * 创建邀请码
   */
  createInvite: async (data: { maxUses: number; expiresAt?: string | null }) => {
    const response = await apiClient.post<Invite>('/auth/invites', {
      max_uses: data.maxUses,
      expires_at: data.expiresAt || null,
    })
    return response.data
  },

  /**
   * 删除邀请码
   */
  deleteInvite: async (id: string) => {
    await apiClient.delete(`/auth/invites/${id}`)
  },

  // ==================== 总题库管理 ====================
  /**
   * 获取所有题目列表
   */
  listAllQuestions: async (filters: any = {}) => {
    const params = new URLSearchParams()

    if (filters.page) params.append('page', filters.page.toString())
    if (filters.page_size) params.append('page_size', filters.page_size.toString())
    if (filters.user_id) params.append('user_id', filters.user_id)
    if (filters.user) params.append('user', filters.user)
    if (filters.subject) params.append('subject', filters.subject)
    if (filters.book_name) params.append('book_name', filters.book_name)
    if (filters.chapter_name) params.append('chapter_name', filters.chapter_name)
    if (filters.type) params.append('type', filters.type)
    if (filters.difficulty) params.append('difficulty', filters.difficulty)
    if (filters.knowledge_point_q) params.append('knowledge_point_q', filters.knowledge_point_q)
    if (filters.search) params.append('search', filters.search)
    if (filters.q) params.append('q', filters.q)
    if (filters.start_date) params.append('start_date', filters.start_date)
    if (filters.end_date) params.append('end_date', filters.end_date)
    if (filters.tags_json?.length) {
      filters.tags_json.forEach((tag: string) => params.append('tags_json', tag))
    }

    const response = await apiClient.get<any>(`/admin/questions?${params}`)
    const data = response.data || {}
    const page = Number(data.page || filters.page || 1)
    const pageSize = Number(data.page_size || filters.page_size || 20)
    const total = Number(data.total || 0)
    return {
      ...data,
      page,
      page_size: pageSize,
      total_pages: Math.ceil(total / pageSize) || 1,
    }
  },

  // ==================== 总组卷管理 ====================
  /**
   * 获取所有组卷列表
   */
  listAllPaperSets: async (filters: any = {}) => {
    const params = new URLSearchParams()

    if (filters.page) params.append('page', filters.page.toString())
    if (filters.page_size) params.append('page_size', filters.page_size.toString())
    if (filters.user_id) params.append('user_id', filters.user_id)
    if (filters.subject) params.append('subject', filters.subject)
    if (filters.search) params.append('search', filters.search)

    const response = await apiClient.get<any>(`/admin/paper-sets?${params}`)
    const data = response.data || {}
    const page = Number(data.page || filters.page || 1)
    const pageSize = Number(data.page_size || filters.page_size || 20)
    const total = Number(data.total || 0)
    return {
      ...data,
      page,
      page_size: pageSize,
      total_pages: Math.ceil(total / pageSize) || 1,
    }
  },

  // ==================== API 日志 ====================
  /**
   * 获取 API 调用日志
   */
  listApiLogs: async (filters: LogFilters = {}) => {
    const params = new URLSearchParams()

    const page = filters.page || 1
    const pageSize = filters.pageSize || filters.page_size || 20
    params.append('page', page.toString())
    params.append('page_size', pageSize.toString())
    if (filters.userId) params.append('user_id', filters.userId)
    if (filters.purpose) params.append('purpose', filters.purpose)
    if (filters.provider) params.append('provider', filters.provider)
    if (filters.startDay) params.append('start_day', filters.startDay)
    if (filters.endDay) params.append('end_day', filters.endDay)
    if (filters.search) params.append('search', filters.search)

    const response = await apiClient.get<PaginatedResponse<ApiCallLog>>(`/admin/api-logs?${params}`)
    const data = response.data as any
    const total = Number(data?.total || 0)
    return {
      ...data,
      page,
      page_size: pageSize,
      total_pages: Math.ceil(total / pageSize) || 1,
    } as PaginatedResponse<ApiCallLog>
  },

  /**
   * 获取 API 调用统计
   */
  getApiStats: async (params: any = {}) => {
    const query = new URLSearchParams()

    if (params.start_date) query.append('start_date', params.start_date)
    if (params.end_date) query.append('end_date', params.end_date)

    const response = await apiClient.get<any>(`/admin/api-logs/stats?${query}`)
    return response.data
  },
}
