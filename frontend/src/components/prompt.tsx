import { useRef } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import { ArrowUp02Icon, Attachment01Icon } from "@hugeicons/core-free-icons"

import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupTextarea } from "@/components/ui/group"

// Input box style: a heavier border and no focus ring
const frame =
  "border-2 bg-card/90 dark:bg-card/90 dark:border-secondary has-[[data-slot=input-group-control]:focus-visible]:ring-0 dark:has-[[data-slot=input-group-control]:focus-visible]:border-ring"

type Props = {
  value: string
  onchange: (value: string) => void
  busy: boolean
  tall?: boolean
  onsend: () => void
  onattach: (file: File) => void
}

/** The chat input: a textarea, an attach button and a send button, roomy on the home layout, compact in a thread. */
export function Prompt({ value, onchange, busy, tall, onsend, onattach }: Props) {
  const picker = useRef<HTMLInputElement>(null)
  const ready = value.trim().length > 0 && !busy

  const attach = (
    <>
      <InputGroupButton variant="ghost" size="icon-sm" aria-label="Attach a document" onClick={() => picker.current?.click()}>
        <HugeiconsIcon icon={Attachment01Icon} />
      </InputGroupButton>
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
    </>
  )
  const send = (
    <InputGroupButton variant="default" size="icon-sm" aria-label="Send question" disabled={!ready} onClick={onsend}>
      <HugeiconsIcon icon={ArrowUp02Icon} />
    </InputGroupButton>
  )
  const textarea = (
    <InputGroupTextarea
      autoFocus
      rows={1}
      value={value}
      aria-label="Question"
      placeholder="Ask about this project's documents"
      className={tall ? "max-h-48 min-h-9" : "max-h-48 min-h-0"}
      onChange={(event) => onchange(event.target.value)}
      onKeyDown={(event) => {
        if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
          event.preventDefault()
          if (ready) onsend()
        }
      }}
    />
  )

  return (
    <InputGroup className={frame}>
      {tall ? (
        <>
          {textarea}
          <InputGroupAddon align="block-end" className="justify-between">
            {attach}
            {send}
          </InputGroupAddon>
        </>
      ) : (
        <>
          <InputGroupAddon align="inline-start" className="self-end">
            {attach}
          </InputGroupAddon>
          {textarea}
          <InputGroupAddon align="inline-end" className="self-end">
            {send}
          </InputGroupAddon>
        </>
      )}
    </InputGroup>
  )
}
