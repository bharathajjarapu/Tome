import { useOutletContext } from "react-router"

import { useDocuments, type Project } from "@/api/queries"
import { Documents } from "@/components/documents"
import { Dropzone } from "@/components/dropzone"
import { Failed, Loading } from "@/components/states"
import { useUploads } from "@/hooks/uploads"

// The ingestion page: add files, watch them become searchable. Chat lives on its own page.
export function DocumentsPage() {
  const project = useOutletContext<Project>()
  const docs = useDocuments(project.id)
  const uploads = useUploads(project.id)

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6 pt-16">
        <header className="space-y-1">
          <p className="text-sm text-muted-foreground">{project.name}</p>
          <h1 className="text-3xl font-semibold tracking-tight">Documents</h1>
        </header>

        <Dropzone onfiles={(files) => void uploads.add(files)} />

        {docs.isPending && <Loading label="Loading" />}
        {docs.error && <Failed title="Load failed" failure={docs.error} />}
        <Documents projectid={project.id} docs={docs.data ?? []} entries={uploads.entries} ondismiss={uploads.dismiss} />
      </div>
    </main>
  )
}
