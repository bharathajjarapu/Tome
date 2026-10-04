import { useRef, useState } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import { Upload01Icon } from "@hugeicons/core-free-icons"

import { Button } from "@/components/ui/button"
import { ACCEPT } from "@/lib/files"
import { cn } from "@/lib/utils"

/** Drop files anywhere on the card, or pick them from the device. */
export function Dropzone({ onfiles }: { onfiles: (files: File[]) => void }) {
  const picker = useRef<HTMLInputElement>(null)
  const [over, setover] = useState(false)

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-xl border-2 border-dashed bg-card/50 px-6 py-10 text-center transition-colors",
        over && "border-ring bg-muted/50",
      )}
      onDragOver={(event) => {
        event.preventDefault()
        setover(true)
      }}
      onDragLeave={(event) => !event.currentTarget.contains(event.relatedTarget as Node) && setover(false)}
      onDrop={(event) => {
        event.preventDefault()
        setover(false)
        onfiles(Array.from(event.dataTransfer.files))
      }}
    >
      <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <HugeiconsIcon icon={Upload01Icon} className="size-5" />
      </div>
      <div className="space-y-1">
        <p className="font-medium">Drop files to add them</p>
        <p className="text-sm text-muted-foreground">They are indexed in the background, then chat can answer from them.</p>
      </div>
      <Button variant="outline" onClick={() => picker.current?.click()}>
        Choose files
      </Button>
      <input
        ref={picker}
        type="file"
        multiple
        accept={ACCEPT}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(event) => {
          onfiles(Array.from(event.target.files ?? []))
          event.target.value = ""
        }}
      />
      <p className="text-xs text-muted-foreground">PDF, Word, PowerPoint, Excel, EPUB, CSV, Markdown and text · up to 25 MB each</p>
    </div>
  )
}
