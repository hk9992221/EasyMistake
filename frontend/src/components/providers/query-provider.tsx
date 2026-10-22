'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/lib/store/auth'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const accountId = useAuthStore((state) => state.user?.id ?? 'anonymous')
  return <AccountQueryProvider key={accountId} accountId={accountId}>{children}</AccountQueryProvider>
}

function AccountQueryProvider({ children, accountId }: { children: React.ReactNode; accountId: string }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 分钟
            refetchOnWindowFocus: false,
          },
        },
      })
  )

  useEffect(() => () => {
    if ((useAuthStore.getState().user?.id ?? 'anonymous') !== accountId) {
      void queryClient.cancelQueries().then(() => queryClient.clear())
    }
  }, [queryClient, accountId])

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
