import { useRef, useState } from "react"
import { ArrowUp, Paperclip } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

/**
 * The chat input. Hand-written because there is nothing to select: the backend serves one model
 * and has no per-message attachment, so this is a textarea, an attach button and a send button.
 */
export function Prompt({
  busy,
  onsend,
  onattach,
}: {
  busy: boolean
  onsend: (question: string) => void
  onattach: (file: File) => void
}) {
  const [question, setquestion] = useState("")
  const picker = useRef<HTMLInputElement>(null)
  const ready = question.trim().length > 0 && !busy

  function send() {
    if (!ready) return
    onsend(question.trim())
    setquestion("")
  }

  return (
    <form
      className="rounded-2xl border bg-card p-2 shadow-xs focus-within:border-ring"
      onSubmit={(event) => {
        event.preventDefault()
        send()
      }}
    >
      <Textarea
        value={question}
        aria-label="Question"
        placeholder="Ask about this project's documents"
        className="max-h-48 min-h-9 resize-none border-0 bg-transparent px-1.5 py-1.5 focus-visible:ring-0 dark:bg-transparent"
        onChange={(event) => setquestion(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault()
            send()
          }
        }}
      />
      <div className="flex items-center justify-between gap-2">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Attach a document"
          onClick={() => picker.current?.click()}
        >
          <Paperclip />
        </Button>
        <input
          ref={picker}
          type="file"
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) onattach(file)
            event.target.value = ""
          }}
        />
        <Button type="submit" size="icon-sm" disabled={!ready} aria-label="Send question">
          <ArrowUp />
        </Button>
      </div>
    </form>
  )
}
