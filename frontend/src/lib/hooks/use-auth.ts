/**
 * 认证相关 Hook
 */

import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/lib/store'

export const useAuth = () => {
  const router = useRouter()
  const { user, token, isAuthenticated, setAuth, clearAuth, updateUser } = useAuthStore()
  const [isInitialized, setIsInitialized] = useState(false)

  // 初始化时从 localStorage 恢复认证状态（兼容后端的键名）
  useEffect(() => {
    // 只在客户端执行
    if (typeof window === 'undefined') {
      setIsInitialized(true)
      return
    }

    // 如果 Zustand store 已经有数据，不需要恢复
    if (isAuthenticated || token) {
      setIsInitialized(true)
      return
    }

    // 从后端的 localStorage 键恢复
    const accessToken = localStorage.getItem('access_token') || localStorage.getItem('auth_token')
    const userInfo = localStorage.getItem('user_info')

    if (accessToken && userInfo) {
      try {
        const user = JSON.parse(userInfo)
        setAuth(user, accessToken)
      } catch (error) {
        console.error('Failed to parse user_info:', error)
      }
    }

    // 标记为已初始化
    setIsInitialized(true)
  }, []) // 只在组件挂载时执行一次

  // 登录
  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      setAuth(data.user, data.access_token)
      // 登录成功后跳转到 dashboard
      router.push('/dashboard')
    },
  })

  // 注册
  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: (data) => {
      setAuth(data.user, data.access_token)
      // 注册成功后跳转到 dashboard
      router.push('/dashboard')
    },
  })

  // 退出登录
  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      clearAuth()
      router.push('/login')
    },
  })

  // 获取当前用户信息
  const { refetch: refetchUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const data = await authApi.getCurrentUser()
      updateUser(data)
      return data
    },
    enabled: isAuthenticated,
    retry: false,
  })

  return {
    user,
    token,
    isAuthenticated,
    login: loginMutation.mutate,
    register: registerMutation.mutate,
    logout: () => logoutMutation.mutate(),
    refetchUser,
    isLoading: loginMutation.isPending || registerMutation.isPending || !isInitialized,
  }
}
