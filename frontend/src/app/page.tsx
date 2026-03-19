'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/use-auth'

export default function HomePage() {
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    if (isLoading) return

    if (isAuthenticated) {
      // 已登录用户重定向到 dashboard
      router.replace('/dashboard')
    } else {
      // 未登录用户重定向到登录页
      router.replace('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // 显示加载状态
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-muted-foreground">加载中...</div>
    </div>
  )
}
