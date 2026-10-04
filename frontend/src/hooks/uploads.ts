import { useCallback, useState } from "react"

import { useUpload } from "@/api/queries"
import { say } from "@/components/states"
import { refusal } from "@/lib/files"

export type Entry = { id: string; name: string; status: "queued" | "uploading" | "failed"; error?: string }

/**
 * Files on their way to the server, one at a time so a big batch is not a request storm.
 * An entry leaves the queue when it succeeds, because the document list takes over from there.
 */
export function useUploads(projectid: string) {
  const upload = useUpload(projectid)
  const [entries, setentries] = useState<Entry[]>([])

  const patch = useCallback(
    (id: string, change: Partial<Entry> | null) =>
      setentries((current) =>
        change ? current.map((entry) => (entry.id === id ? { ...entry, ...change } : entry)) : current.filter((entry) => entry.id !== id),
      ),
    [],
  )

  const add = useCallback(
    async (files: File[]) => {
      const queued = files.map((file) => ({ id: crypto.randomUUID(), name: file.name, status: "queued" as const }))
      setentries((current) => [...current, ...queued])
      for (const [position, file] of files.entries()) {
        const { id } = queued[position]
        const refused = refusal(file)
        if (refused) {
          patch(id, { status: "failed", error: refused })
          continue
        }
        patch(id, { status: "uploading" })
        try {
          await upload.mutateAsync(file)
          patch(id, null)
        } catch (failure) {
          patch(id, { status: "failed", error: say(failure) })
        }
      }
    },
    [patch, upload],
  )

  return { entries, add, dismiss: (id: string) => patch(id, null) }
}
