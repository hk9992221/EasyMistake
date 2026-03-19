'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store/auth'
import { SESSION_TIMEOUT } from '@/lib/constants/session'
import { AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

/**
 * Session timeout warning component.
 */
export function SessionWarning() {
  const router = useRouter()
  const { clearAuth } = useAuthStore()
  const [remainingMinutes, setRemainingMinutes] = useState<number | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const totalTimeoutMinutes = Math.floor(SESSION_TIMEOUT / 60000)

  useEffect(() => {
    const handleWarning = (event: CustomEvent<{ remainingMinutes: number }>) => {
      setRemainingMinutes(event.detail.remainingMinutes)
      setShowWarning(true)
    }

    window.addEventListener('session-warning', handleWarning as EventListener)
    return () => {
      window.removeEventListener('session-warning', handleWarning as EventListener)
    }
  }, [])

  const handleLogout = () => {
    clearAuth()
    router.push('/login')
  }

  const handleContinue = () => {
    setShowWarning(false)
    setRemainingMinutes(null)
  }

  if (!showWarning || remainingMinutes === null) {
    return null
  }

  return (
    <div className="fixed left-4 right-4 top-4 z-50 md:left-auto md:w-96">
      <Alert variant="warning" className="border-orange-500 bg-orange-50 dark:bg-orange-950">
        <AlertCircle className="h-4 w-4 text-orange-600" />
        <AlertDescription className="space-y-2">
          <div>
            <p className="font-medium text-orange-900 dark:text-orange-100">会话即将过期</p>
            <p className="text-sm text-orange-700 dark:text-orange-300">
              您已连续 {Math.max(totalTimeoutMinutes - remainingMinutes, 0)} 分钟没有活动，
              还有 <strong>{remainingMinutes}</strong> 分钟会话将自动过期。
            </p>
          </div>
          <div className="mt-2 flex gap-2">
            <Button size="sm" onClick={handleContinue} className="bg-orange-600 hover:bg-orange-700">
              继续使用
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleLogout}
              className="border-orange-600 text-orange-600 hover:bg-orange-100"
            >
              立即登出
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  )
}
