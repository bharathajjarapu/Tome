import { HugeiconsIcon } from "@hugeicons/react"
import { Alert02Icon, Cancel01Icon, Delete02Icon, File02Icon } from "@hugeicons/core-free-icons"

import { indexing, useDeleteDocument, type Doc } from "@/api/queries"
import { Failed } from "@/components/states"
import {
  Attachment,
  AttachmentAction,
  AttachmentActions,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment"
import { Spinner } from "@/components/ui/spinner"
import type { Entry } from "@/hooks/uploads"
import { ago, extension } from "@/lib/files"

/** Backend document states, in the vocabulary the Attachment component already speaks. */
const SHOWN = {
  uploaded: "uploading",
  processing: "processing",
  indexed: "done",
  failed: "error",
} as const

const SAYS = {
  uploaded: "Queued",
  processing: "Indexing",
  indexed: "",
  failed: "Failed",
} as const

const kind = (name: string) => extension(name).toUpperCase() || "FILE"

// One number and what it counts
function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-card px-4 py-3 ring-1 ring-foreground/10">
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

/** Where every file stands: counts first, then files still being sent, then what the server holds. */
export function Documents({
  projectid,
  docs,
  entries,
  ondismiss,
}: {
  projectid: string
  docs: Doc[]
  entries: Entry[]
  ondismiss: (id: string) => void
}) {
  const remove = useDeleteDocument(projectid)
  const ready = docs.filter((doc) => doc.state === "indexed").length
  const failed = docs.filter((doc) => doc.state === "failed").length

  return (
    <section className="flex flex-col gap-4" aria-label="Library">
      {docs.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <Stat label="Ready" value={ready} />
          <Stat label="Indexing" value={docs.filter(indexing).length} />
          <Stat label="Failed" value={failed} />
        </div>
      )}
      {remove.error && <Failed title="Delete failed" failure={remove.error} />}

      <ul className="flex flex-col gap-2">
        {entries.map((entry) => (
          <li key={entry.id}>
            <Attachment className="w-full" state={entry.status === "failed" ? "error" : "uploading"}>
              <AttachmentMedia>
                {entry.status === "failed" ? <HugeiconsIcon icon={Alert02Icon} /> : <Spinner />}
              </AttachmentMedia>
              <AttachmentContent>
                <AttachmentTitle>{entry.name}</AttachmentTitle>
                <AttachmentDescription>
                  {entry.status === "failed" ? entry.error : entry.status === "queued" ? "Queued" : "Uploading"}
                </AttachmentDescription>
              </AttachmentContent>
              {entry.status === "failed" && (
                <AttachmentActions>
                  <AttachmentAction aria-label={`Dismiss ${entry.name}`} onClick={() => ondismiss(entry.id)}>
                    <HugeiconsIcon icon={Cancel01Icon} />
                  </AttachmentAction>
                </AttachmentActions>
              )}
            </Attachment>
          </li>
        ))}
        {docs.map((doc) => (
          <li key={doc.id}>
            <Attachment className="w-full" state={SHOWN[doc.state]}>
              <AttachmentMedia>
                {indexing(doc) ? <Spinner /> : <HugeiconsIcon icon={doc.state === "failed" ? Alert02Icon : File02Icon} />}
              </AttachmentMedia>
              <AttachmentContent>
                <AttachmentTitle>{doc.filename}</AttachmentTitle>
                <AttachmentDescription>
                  {[kind(doc.filename), doc.error ?? SAYS[doc.state], ago(doc.created_at)].filter(Boolean).join(" · ")}
                </AttachmentDescription>
              </AttachmentContent>
              <AttachmentActions>
                <AttachmentAction
                  aria-label={`Delete ${doc.filename}`}
                  disabled={remove.isPending && remove.variables === doc.id}
                  onClick={() => remove.mutate(doc.id)}
                >
                  <HugeiconsIcon icon={Delete02Icon} />
                </AttachmentAction>
              </AttachmentActions>
            </Attachment>
          </li>
        ))}
      </ul>
    </section>
  )
}
