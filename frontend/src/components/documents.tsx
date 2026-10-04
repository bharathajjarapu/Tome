import { HugeiconsIcon } from "@hugeicons/react"
import { Alert02Icon, Delete02Icon, File02Icon } from "@hugeicons/core-free-icons"

import { indexing, useDeleteDocument, type Doc } from "@/api/queries"
import { Failed } from "@/components/states"
import {
  Attachment,
  AttachmentAction,
  AttachmentActions,
  AttachmentContent,
  AttachmentDescription,
  AttachmentGroup,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment"
import { Spinner } from "@/components/ui/spinner"

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
  indexed: "Ready to answer questions",
  failed: "Failed",
} as const

export function Documents({ projectid, docs }: { projectid: string; docs: Doc[] }) {
  const remove = useDeleteDocument(projectid)
  return (
    <>
      {remove.error && <Failed title="Could not delete the document" failure={remove.error} />}
      <AttachmentGroup className="flex-col overflow-x-visible *:data-[slot=attachment]:w-full">
        {docs.map((doc) => (
          <Attachment key={doc.id} state={SHOWN[doc.state]}>
            <AttachmentMedia>
              {indexing(doc) ? (
                <Spinner />
              ) : doc.state === "failed" ? (
                <HugeiconsIcon icon={Alert02Icon} />
              ) : (
                <HugeiconsIcon icon={File02Icon} />
              )}
            </AttachmentMedia>
            <AttachmentContent>
              <AttachmentTitle>{doc.filename}</AttachmentTitle>
              <AttachmentDescription>{doc.error ?? SAYS[doc.state]}</AttachmentDescription>
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
        ))}
      </AttachmentGroup>
    </>
  )
}
