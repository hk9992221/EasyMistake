/**
 * 认证相关 API
 */

import { apiClient } from './client'
import { User } from '@/types/models'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  inviteCode?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface UserDashboardResponse {
  start_date: string
  end_date: string
  total_calls: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  total_cost_usd: number
  total_cost_cny: number
  avg_latency_ms: number | null
  calls_by_date: Record<string, { count: number; cost: number }>
  calls_by_purpose: Record<string, { count: number; cost: number }>
  calls_by_model: Record<string, { count: number; cost: number }>
}

export const authApi = {
  /**
   * 用户登录
   */
  login: async (data: LoginRequest) => {
    const formData = new URLSearchParams()
    formData.set('username', data.email)
    formData.set('password', data.password)

    const response = await apiClient.post<AuthResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  /**
   * 用户注册
   */
  register: async (data: RegisterRequest) => {
    const response = await apiClient.post<AuthResponse>('/auth/register', {
      email: data.email,
      password: data.password,
      invite_code: data.inviteCode || null,
    })
    return response.data
  },

  /**
   * 获取当前用户信息
   */
  getCurrentUser: async () => {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  /**
   * 获取当前用户 dashboard 成本统计
   */
  getDashboard: async (params: { start_day?: string; end_day?: string } = {}) => {
    const query = new URLSearchParams()
    if (params.start_day) query.append('start_day', params.start_day)
    if (params.end_day) query.append('end_day', params.end_day)
    const response = await apiClient.get<UserDashboardResponse>(`/auth/me/dashboard?${query}`)
    return response.data
  },

  /**
   * 退出登录
   */
  logout: async () => {
    await apiClient.post('/auth/logout')
  },
}
