import { useCallback, useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"

import { post } from "@/api/client"
import type { Conversation, Source } from "@/api/queries"
import { sse } from "@/api/stream"

export type Turn = {
  id: string
  role: "user" | "assistant"
  content: string
  citations: Source[]
}

type Started = { conversation_id: string; message_id: string }

export function toturns(conversation: Conversation): Turn[] {
  return conversation.messages.map((message) => ({
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations,
  }))
}

function reason(failure: unknown): string {
  return failure instanceof Error ? failure.message : "The answer could not be streamed"
}

/**
 * One question: store it, stream the answer into the transcript, keep the citations it cites.
 * Nothing is refetched at the end — the finished thread is written straight into the cache.
 */
export function useChat(
  projectid: string,
  conversationid: string | undefined,
  initial: Turn[],
  onstarted: (conversationid: string) => void,
) {
  const client = useQueryClient()
  const [turns, setturns] = useState(initial)
  const [streaming, setstreaming] = useState(false)
  const [error, seterror] = useState<string | null>(null)
  // The transcript is read back inside the stream loop, where state would be a stale closure.
  const latest = useRef(initial)
  const thread = useRef(conversationid)
  const inflight = useRef<AbortController | null>(null)

  // Leaving the page must not leave a stream running against a component that is gone.
  useEffect(() => () => inflight.current?.abort(), [])

  const update = useCallback((change: (turns: Turn[]) => Turn[]) => {
    latest.current = change(latest.current)
    setturns(latest.current)
  }, [])

  const ask = useCallback(
    async (question: string) => {
      seterror(null)
      const answerid = crypto.randomUUID()
      update((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "user", content: question, citations: [] },
        { id: answerid, role: "assistant", content: "", citations: [] },
      ])
      const patch = (change: (turn: Turn) => Turn) =>
        update((current) => current.map((turn) => (turn.id === answerid ? change(turn) : turn)))

      const controller = new AbortController()
      inflight.current = controller
      setstreaming(true)
      try {
        const started = await post<Started>(`/projects/${projectid}/chat`, {
          question,
          conversation_id: thread.current ?? null,
        })
        const isnew = thread.current === undefined
        thread.current = started.conversation_id
        let ended = false
        for await (const frame of sse(
          `/projects/${projectid}/chat/stream?message_id=${started.message_id}`,
          controller.signal,
        )) {
          const data: unknown = JSON.parse(frame.data)
          if (frame.event === "token") {
            const { text } = data as { text: string }
            patch((turn) => ({ ...turn, content: turn.content + text }))
          } else if (frame.event === "citation") {
            patch((turn) => ({ ...turn, citations: [...turn.citations, data as Source] }))
          } else if (frame.event === "error") {
            throw new Error((data as { detail?: string }).detail || "The answer could not be generated")
          } else if (frame.event === "message_end") {
            ended = true
          }
        }
        // A stream that simply stops is a failure, not a short answer.
        if (!ended) throw new Error("The answer ended before it was finished")

        client.setQueryData<Conversation>(["conversation", started.conversation_id], {
          id: started.conversation_id,
          project_id: projectid,
          messages: latest.current.map((turn) => ({
            id: turn.id,
            role: turn.role,
            content: turn.content,
            citations: turn.citations,
          })),
        })
        if (isnew) client.invalidateQueries({ queryKey: ["conversations", projectid] })
        onstarted(started.conversation_id)
      } catch (failure) {
        if (!controller.signal.aborted) seterror(reason(failure))
        // The question may already be stored; let the next read show it.
        if (thread.current) client.invalidateQueries({ queryKey: ["conversation", thread.current] })
        client.invalidateQueries({ queryKey: ["conversations", projectid] })
      } finally {
        setstreaming(false)
      }
    },
    [client, onstarted, projectid, update],
  )

  return { turns, streaming, error, ask }
}
