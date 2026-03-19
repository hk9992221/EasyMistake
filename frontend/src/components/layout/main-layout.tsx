'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/hooks/use-auth'
import { Sidebar } from './sidebar'
import { SessionWarning } from '@/components/session-warning'
import { cn } from '@/lib/utils'

interface MainLayoutProps {
  children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  const { isAuthenticated, isLoading, user, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const isAdmin = user?.role === 'ADMIN'

  const mobileNavItems = [
    { title: '首页', href: '/dashboard' },
    { title: '录题', href: '/dashboard/extract' },
    { title: '试题', href: '/dashboard/questions' },
    { title: '组卷', href: '/dashboard/paper-sets' },
  ]

  if (isAdmin) {
    mobileNavItems.push({ title: '管理', href: '/dashboard/admin/questions' })
  }

  const isMobileNavActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard'
    }
    return pathname?.startsWith(href)
  }

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="hidden md:flex">
        <Sidebar />
      </div>
      <main className="flex-1 overflow-y-auto bg-background">
        <div className="border-b bg-card px-4 py-3 md:hidden">
          <div className="mb-3 flex items-center justify-between">
            <h1 className="text-base font-semibold">题库管理系统</h1>
            <button
              onClick={() => logout()}
              className="text-sm text-muted-foreground"
            >
              退出
            </button>
          </div>
          <nav className="flex gap-2 overflow-x-auto">
            {mobileNavItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'whitespace-nowrap rounded-md border px-3 py-1.5 text-sm',
                  isMobileNavActive(item.href)
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-background text-foreground',
                )}
              >
                {item.title}
              </Link>
            ))}
          </nav>
        </div>
        <SessionWarning />
        {children}
      </main>
    </div>
  )
}
