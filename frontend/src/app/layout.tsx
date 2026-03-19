import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { QueryProvider } from '@/components/providers/query-provider'
import { ThemeProvider } from '@/components/providers/theme-provider'
import { SessionTimeoutProvider } from '@/components/providers/session-timeout-provider'
import { Toaster } from '@/components/ui/toaster'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '题库管理系统',
  description: '个人题库管理系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <SessionTimeoutProvider>
            <QueryProvider>
              {children}
              <Toaster />
            </QueryProvider>
          </SessionTimeoutProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
