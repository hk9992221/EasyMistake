import { MainLayout } from '@/components/layout/main-layout'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <MainLayout>{children}</MainLayout>
}
