'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { imagesApi } from '@/lib/api/images'
import { useAuthStore } from '@/lib/store/auth'

interface AuthenticatedImageProps {
  imageId: string
  alt: string
  className?: string
}

export function AuthenticatedImage({ imageId, alt, className }: AuthenticatedImageProps) {
  const userId = useAuthStore((state) => state.user?.id)
  const { data, isError, refetch } = useQuery({
    queryKey: ['image-file', userId, imageId],
    queryFn: ({ signal }) => imagesApi.getFile(imageId, signal),
    enabled: Boolean(userId && imageId),
    staleTime: 5 * 60 * 1000,
    gcTime: 60 * 1000,
    retry: 1,
  })
  const [preview, setPreview] = useState<{ blob: Blob; url: string } | null>(null)

  useEffect(() => {
    if (!data) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(data)
    setPreview({ blob: data, url })
    return () => URL.revokeObjectURL(url)
  }, [data])

  // Never display the previous account's or previous question's cached image.
  if (userId && data && preview?.blob === data) {
    return <img src={preview.url} alt={alt} className={className} />
  }
  if (isError) {
    return <button type="button" onClick={() => refetch()} className="rounded border p-3 text-sm text-muted-foreground">
      {alt}加载失败，点击重试
    </button>
  }
  return <span role="status" className="block p-3 text-sm text-muted-foreground">{alt}加载中…</span>
}
