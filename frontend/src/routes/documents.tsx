import { useRef } from "react"
import { Upload } from "lucide-react"
import { useParams } from "react-router"

import { useDocuments, useUpload } from "@/api/queries"
import { Documents } from "@/components/documents"
import { Failed, Loading } from "@/components/states"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"

export function DocumentsPage() {
  const { projectid = "" } = useParams()
  const docs = useDocuments(projectid)
  const upload = useUpload(projectid)
  const picker = useRef<HTMLInputElement>(null)

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 overflow-y-auto p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-medium">Documents</h1>
        <Button disabled={upload.isPending} onClick={() => picker.current?.click()}>
          <Upload /> Upload
        </Button>
        <input
          ref={picker}
          type="file"
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) upload.mutate(file)
            event.target.value = ""
          }}
        />
      </div>

      {upload.error && <Failed title="Upload rejected" failure={upload.error} />}
      {docs.isPending && <Loading label="Loading documents" />}
      {docs.error && <Failed title="Could not load documents" failure={docs.error} />}

      {docs.data?.length === 0 ? (
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Upload />
            </EmptyMedia>
            <EmptyTitle>No documents yet</EmptyTitle>
            <EmptyDescription>
              Upload one and it will be indexed in the background. Answers only come from these.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        docs.data && <Documents projectid={projectid} docs={docs.data} />
      )}
    </main>
  )
}
