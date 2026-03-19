/**
 * 认证状态管理
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User } from '@/types/models'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: User, token: string) => void
  clearAuth: () => void
  updateUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user, token) => {
        // 同时保存到 localStorage 兼容后端的键名
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token)
          localStorage.setItem('access_token', token)
          localStorage.setItem('user_info', JSON.stringify(user))
        }
        set({ user, token, isAuthenticated: true })
      },

      clearAuth: () => {
        // 清除所有相关的 localStorage 键
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('access_token')
          localStorage.removeItem('user_info')
          localStorage.removeItem('auth-storage')
          document.cookie = 'auth_token=; Max-Age=0; path=/'
          document.cookie = 'access_token=; Max-Age=0; path=/'
        }
        set({ user: null, token: null, isAuthenticated: false })
      },

      updateUser: (user) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('user_info', JSON.stringify(user))
        }
        set({ user })
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
