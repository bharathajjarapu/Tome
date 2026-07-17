/** Every server call the UI makes. Components import these, never `fetch`. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api, post, type Schemas } from "@/api/client"

export type Project = Schemas["ProjectOut"]
export type Doc = Schemas["DocumentOut"]
export type Conversation = Schemas["ConversationOut"]
export type Summary = Schemas["ConversationSummary"]
export type Message = Schemas["MessageOut"]

/** A stored citation, plus the document name the live stream sends and the database does not. */
export type Source = Schemas["CitationOut"] & { document_name?: string }

export function useProjects() {
  return useQuery({ queryKey: ["projects"], queryFn: () => api<Project[]>("/projects") })
}

export function useProject(projectid: string) {
  return useQuery({
    queryKey: ["project", projectid],
    queryFn: () => api<Project>(`/projects/${projectid}`),
  })
}

export function useCreateProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => post<Project>("/projects", { name }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["projects"] }),
  })
}

export const indexing = (doc: Doc) => doc.state === "uploaded" || doc.state === "processing"

const pending = (docs: Doc[] | undefined) => docs?.filter(indexing) ?? []

/** Poll quickly at first, then ease off, so a long ingest does not become a request storm. */
export function interval(docs: Doc[] | undefined, now = Date.now()): number | false {
  const waiting = pending(docs)
  if (waiting.length === 0) return false
  // The newest upload sets the pace: it is the one someone is watching.
  const newest = Math.max(...waiting.map((doc) => Date.parse(doc.created_at)))
  return Math.min(Math.max(1500, 1500 + (now - newest) / 10), 15000)
}

export function useDocuments(projectid: string) {
  return useQuery({
    queryKey: ["documents", projectid],
    queryFn: () => api<Doc[]>(`/projects/${projectid}/documents`),
    // The only polling in the app, and it stops as soon as everything has settled.
    refetchInterval: (query) => interval(query.state.data),
  })
}

export function useUpload(projectid: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append("file", file)
      return api<Doc>(`/projects/${projectid}/documents`, { method: "POST", body: form })
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["documents", projectid] }),
  })
}

export function useDeleteDocument(projectid: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (documentid: string) =>
      api<void>(`/documents/${documentid}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["documents", projectid] }),
  })
}

export function useConversations(projectid: string) {
  return useQuery({
    queryKey: ["conversations", projectid],
    queryFn: () => api<Summary[]>(`/projects/${projectid}/conversations`),
  })
}

export function useConversation(conversationid: string | undefined) {
  return useQuery({
    queryKey: ["conversation", conversationid],
    queryFn: () => api<Conversation>(`/conversations/${conversationid}`),
    enabled: conversationid !== undefined,
    // Append-only, and this app writes every append into the cache itself.
    staleTime: Infinity,
  })
}
