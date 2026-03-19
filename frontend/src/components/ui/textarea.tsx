import * as React from "react"

import { cn } from "@/lib/utils"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, onKeyDown, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        onKeyDown={(event) => {
          const shouldWrap = event.key === "$" || event.key === "￥"
          const el = event.currentTarget
          const start = el.selectionStart ?? 0
          const end = el.selectionEnd ?? 0
          const hasSelection = end > start

          if (shouldWrap && hasSelection && !event.ctrlKey && !event.metaKey && !event.altKey) {
            event.preventDefault()
            const selected = el.value.slice(start, end)
            el.setRangeText(`$${selected}$`, start, end, "end")
            el.dispatchEvent(new Event("input", { bubbles: true }))
          }

          onKeyDown?.(event)
        }}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }
