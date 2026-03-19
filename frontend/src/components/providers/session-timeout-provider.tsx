'use client'

import { useEffect, useRef, useCallback } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import { SESSION_TIMEOUT, WARNING_TIME, CHECK_INTERVAL } from '@/lib/constants/session'

/**
 * 会话超时Provider
 * 监听用户活动，长时间不活动自动登出
 */
export function SessionTimeoutProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, clearAuth } = useAuthStore()

  const lastActivityRef = useRef<Date>(new Date())
  const warningShownRef = useRef(false)
  const timeoutRef = useRef<NodeJS.Timeout>()

  // 更新最后活动时间
  const updateActivity = useCallback(() => {
    lastActivityRef.current = new Date()
    warningShownRef.current = false
  }, [])

  // 检查会话是否超时
  const checkSessionTimeout = useCallback(() => {
    if (!isAuthenticated) return

    const now = new Date()
    const inactiveTime = now.getTime() - lastActivityRef.current.getTime()

    // 显示警告
    if (inactiveTime >= SESSION_TIMEOUT - WARNING_TIME && inactiveTime < SESSION_TIMEOUT && !warningShownRef.current) {
      const remainingMinutes = Math.ceil((SESSION_TIMEOUT - inactiveTime) / 60000)
      console.warn(`会话即将在 ${remainingMinutes} 分钟后过期`)
      warningShownRef.current = true

      // 可以在这里添加警告提示UI
      if (typeof window !== 'undefined') {
        // 使用自定义事件或toast来显示警告
        const event = new CustomEvent('session-warning', {
          detail: { remainingMinutes }
        })
        window.dispatchEvent(event)
      }
    }

    // 会话超时，自动登出
    if (inactiveTime >= SESSION_TIMEOUT) {
      console.log('会话已超时，自动登出')
      clearAuth()
      if (typeof window !== 'undefined') {
        // 保存当前路径，登出后可以重定向回来
        sessionStorage.setItem('redirect_after_login', pathname)
        router.push('/login')
      }
    }
  }, [isAuthenticated, pathname, clearAuth, router])

  // 设置活动监听
  useEffect(() => {
    if (!isAuthenticated) return

    // 监听用户活动事件
    const activityEvents = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click',
    ]

    const handleActivity = () => {
      updateActivity()
    }

    // 添加事件监听
    activityEvents.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true })
    })

    // 定期检查会话超时
    timeoutRef.current = setInterval(checkSessionTimeout, CHECK_INTERVAL)

    // 初始化活动时间
    updateActivity()

    // 清理函数
    return () => {
      activityEvents.forEach((event) => {
        window.removeEventListener(event, handleActivity)
      })
      if (timeoutRef.current) {
        clearInterval(timeoutRef.current)
      }
    }
  }, [isAuthenticated, updateActivity, checkSessionTimeout])

  // 监听认证状态变化
  useEffect(() => {
    if (isAuthenticated) {
      updateActivity()
    }
  }, [isAuthenticated, updateActivity])

  return <>{children}</>
}
