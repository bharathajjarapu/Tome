import { FileText, Trash2, TriangleAlert } from "lucide-react"

import type { Doc } from "@/api/queries"
import { useDeleteDocument } from "@/api/queries"
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
    <AttachmentGroup className="flex-col overflow-x-visible *:data-[slot=attachment]:w-full">
      {docs.map((doc) => (
        <Attachment key={doc.id} state={SHOWN[doc.state]}>
          <AttachmentMedia>
            {doc.state === "uploaded" || doc.state === "processing" ? (
              <Spinner />
            ) : doc.state === "failed" ? (
              <TriangleAlert />
            ) : (
              <FileText />
            )}
          </AttachmentMedia>
          <AttachmentContent>
            <AttachmentTitle>{doc.filename}</AttachmentTitle>
            <AttachmentDescription>{doc.error ?? SAYS[doc.state]}</AttachmentDescription>
          </AttachmentContent>
          <AttachmentActions>
            <AttachmentAction
              aria-label={`Delete ${doc.filename}`}
              disabled={remove.isPending}
              onClick={() => remove.mutate(doc.id)}
            >
              <Trash2 />
            </AttachmentAction>
          </AttachmentActions>
        </Attachment>
      ))}
    </AttachmentGroup>
  )
}
