/**
 * API 客户端基础配置
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { API_BASE_URL, API_PREFIX } from '../constants'
import { useAuthStore } from '../store/auth'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}${API_PREFIX}`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // 请求拦截器
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // 优先从 Zustand store 获取 token，如果没有则从 localStorage 获取
        let token = useAuthStore.getState().token

        if (!token && typeof window !== 'undefined') {
          // 兼容后端的键名
          token = localStorage.getItem('access_token') || localStorage.getItem('auth_token')
        }

        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response
      },
      (error: AxiosError) => {
        if (error.response) {
          const status = error.response.status

          // 处理 401 未授权错误
          if (status === 401) {
            // 使用 Zustand store 清除认证状态
            useAuthStore.getState().clearAuth()
            if (typeof window !== 'undefined') {
              window.location.href = '/login'
            }
          }

          // 处理其他错误
          return Promise.reject({
            status,
            message:
              (error.response.data as any)?.message ||
              (error.response.data as any)?.detail ||
              '请求失败',
            data: error.response.data,
          })
        }

        // 网络错误
        if (error.request) {
          return Promise.reject({
            message: '网络错误，请检查您的网络连接',
          })
        }

        return Promise.reject({
          message: error.message || '未知错误',
        })
      }
    )
  }

  public getInstance(): AxiosInstance {
    return this.client
  }

  // HTTP 方法封装
  public get<T>(url: string, config?: any) {
    return this.client.get<T>(url, config)
  }

  public post<T>(url: string, data?: any, config?: any) {
    return this.client.post<T>(url, data, config)
  }

  public put<T>(url: string, data?: any, config?: any) {
    return this.client.put<T>(url, data, config)
  }

  public patch<T>(url: string, data?: any, config?: any) {
    return this.client.patch<T>(url, data, config)
  }

  public delete<T>(url: string, config?: any) {
    return this.client.delete<T>(url, config)
  }
}

// 创建单例
export const apiClient = new ApiClient()
