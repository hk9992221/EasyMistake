'use client'

import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Upload, X, Loader2 } from 'lucide-react'
import { imagesApi, questionsApi } from '@/lib/api'
import { useToast } from '@/lib/hooks/use-toast'

interface QuestionImage {
  image_id: string
  order_index: number
  url?: string
}

interface QuestionImageUploadProps {
  questionId: string
  images: QuestionImage[]
  onImagesChange: (images: QuestionImage[]) => void
}

export function QuestionImageUpload({ questionId, images, onImagesChange }: QuestionImageUploadProps) {
  const { toast } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setIsUploading(true)
    try {
      // 上传所有图片
      const uploadPromises = Array.from(files).map(async (file) => {
        const uploadedImage = await imagesApi.upload(file)
        await questionsApi.addImage(questionId, uploadedImage.id)
        return {
          image_id: uploadedImage.id,
          order_index: images.length + Array.from(files).indexOf(file) + 1,
          url: uploadedImage.storage_url,
        }
      })

      const newImages = await Promise.all(uploadPromises)
      onImagesChange([...images, ...newImages])

      toast({
        title: '上传成功',
        description: `成功上传 ${newImages.length} 张图片`,
      })
    } catch (error) {
      console.error('Upload failed:', error)
      toast({
        title: '上传失败',
        description: '图片上传失败，请重试',
        variant: 'destructive',
      })
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleRemoveImage = async (imageId: string) => {
    try {
      await questionsApi.removeImage(questionId, imageId)
      onImagesChange(images.filter(img => img.image_id !== imageId))
      toast({
        title: '已移除',
        description: '图片已从题干中移除',
      })
    } catch (error) {
      console.error('Remove failed:', error)
      toast({
        title: '移除失败',
        description: '无法移除图片',
        variant: 'destructive',
      })
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* 上传按钮 */}
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              id="image-upload"
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              variant="outline"
              className="gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  上传中...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  上传图片
                </>
              )}
            </Button>
            <span className="text-sm text-muted-foreground">
              支持上传多张图片，格式：jpg, png, gif
            </span>
          </div>

          {/* 图片列表 */}
          {images.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {images
                .sort((a, b) => a.order_index - b.order_index)
                .map((image) => (
                  <div key={image.image_id} className="group relative aspect-square">
                    <img
                      src={image.url}
                      alt={`题干图片 ${image.order_index}`}
                      className="w-full h-full object-cover rounded-lg border"
                    />
                    <Button
                      size="icon"
                      variant="destructive"
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleRemoveImage(image.image_id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                    <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                      #{image.order_index}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* 空状态 */}
          {images.length === 0 && !isUploading && (
            <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
              <Upload className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>暂无图片</p>
              <p className="text-sm mt-2">点击上方按钮上传题干图片</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
