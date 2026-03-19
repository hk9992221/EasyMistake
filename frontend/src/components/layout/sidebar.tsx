'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/hooks/use-auth'
import { cn } from '@/lib/utils'
import {
  BookOpen,
  FileText,
  Layers,
  CalendarClock,
  Settings,
  LogOut,
  LayoutDashboard,
  Users,
  FileQuestion,
  History
} from 'lucide-react'

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const isAdmin = user?.role === 'ADMIN'

  const mainNavItems = [
    {
      title: '录入试题',
      href: '/dashboard/extract',
      icon: BookOpen,
    },
    {
      title: '试题',
      href: '/dashboard/questions',
      icon: FileText,
    },
    {
      title: '组卷',
      href: '/dashboard/paper-sets',
      icon: Layers,
    },
    {
      title: '今日复习',
      href: '/dashboard/reviews',
      icon: CalendarClock,
    },
  ]

  const adminNavItems = [
    {
      title: '总试题管理',
      href: '/dashboard/admin/questions',
      icon: FileQuestion,
    },
    {
      title: '用户管理',
      href: '/dashboard/admin/users',
      icon: Users,
    },
    {
      title: '总组卷管理',
      href: '/dashboard/admin/paper-sets',
      icon: LayoutDashboard,
    },
    {
      title: 'API 使用日志',
      href: '/dashboard/admin/api-logs',
      icon: History,
    },
  ]

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="border-b p-6">
        <h1 className="text-xl font-bold">题库管理系统</h1>
        {user && (
          <p className="mt-1 text-sm text-muted-foreground">
            {user.email} {isAdmin && '(管理员)'}
          </p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        {/* 主导航 */}
        <div className="px-3 pb-4">
          <h2 className="mb-2 px-3 text-xs font-semibold uppercase text-muted-foreground">
            主功能
          </h2>
          <nav className="space-y-1">
            {mainNavItems.map((item) => {
              const isActive = pathname?.startsWith(item.href)
              const Icon = item.icon
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.title}
                </Link>
              )
            })}
          </nav>
        </div>

        {/* 管理员导航 */}
        {isAdmin && (
          <div className="border-t px-3 pt-4">
            <h2 className="mb-2 px-3 text-xs font-semibold uppercase text-muted-foreground">
              管理员功能
            </h2>
            <nav className="space-y-1">
              {adminNavItems.map((item) => {
                const isActive = pathname?.startsWith(item.href)
                const Icon = item.icon
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.title}
                  </Link>
                )
              })}
            </nav>
          </div>
        )}
      </div>

      {/* 底部操作 */}
      <div className="border-t p-4">
        <button
          onClick={() => logout()}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </button>
      </div>
    </div>
  )
}
