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

const settling = (docs: Doc[] | undefined) =>
  docs?.some((doc) => doc.state === "uploaded" || doc.state === "processing") ?? false

export function useDocuments(projectid: string) {
  return useQuery({
    queryKey: ["documents", projectid],
    queryFn: () => api<Doc[]>(`/projects/${projectid}/documents`),
    // The only polling in the app, and it stops as soon as everything has settled.
    refetchInterval: (query) => (settling(query.state.data) ? 1500 : false),
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
