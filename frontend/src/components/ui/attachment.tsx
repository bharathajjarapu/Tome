import type { ComponentProps } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// A file row: media on the left, name and detail in the middle, actions on the right
function Attachment({ className, state = "done", ...props }: ComponentProps<"div"> & { state?: "uploading" | "processing" | "error" | "done" }) {
  return (
    <div
      data-slot="attachment"
      data-state={state}
      className={cn(
        "group/attachment relative flex w-fit max-w-full min-w-40 shrink-0 flex-wrap items-center gap-2 rounded-xl border bg-card text-sm text-card-foreground transition-colors focus-within:ring-1 focus-within:ring-ring/50 has-data-[slot=attachment-content]:px-2.5 has-data-[slot=attachment-content]:py-2 has-data-[slot=attachment-media]:p-2 data-[state=error]:border-destructive/30",
        className,
      )}
      {...props}
    />
  )
}

function AttachmentMedia({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="attachment-media"
      className={cn(
        "relative flex aspect-square w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted text-foreground group-data-[state=error]/attachment:bg-destructive/10 group-data-[state=error]/attachment:text-destructive [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    />
  )
}

function AttachmentContent({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="attachment-content" className={cn("max-w-full min-w-0 flex-1 leading-tight", className)} {...props} />
}

function AttachmentTitle({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      data-slot="attachment-title"
      className={cn("block max-w-full min-w-0 truncate font-medium group-data-[state=processing]/attachment:shimmer group-data-[state=uploading]/attachment:shimmer", className)}
      {...props}
    />
  )
}

function AttachmentDescription({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      data-slot="attachment-description"
      className={cn("mt-0.5 block max-w-full min-w-0 truncate text-xs text-muted-foreground group-data-[state=error]/attachment:text-destructive/80", className)}
      {...props}
    />
  )
}

function AttachmentActions({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="attachment-actions" className={cn("relative z-20 flex shrink-0 items-center", className)} {...props} />
}

function AttachmentAction({ variant = "ghost", size = "icon-xs", ...props }: ComponentProps<typeof Button>) {
  return <Button data-slot="attachment-action" variant={variant} size={size} {...props} />
}

export { Attachment, AttachmentMedia, AttachmentContent, AttachmentTitle, AttachmentDescription, AttachmentActions, AttachmentAction }
