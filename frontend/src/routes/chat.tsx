import { useCallback, useMemo } from "react"
import { MessagesSquare } from "lucide-react"
import { useNavigate, useParams } from "react-router"

import { useConversation, useDocuments, useUpload } from "@/api/queries"
import { toturns, useChat } from "@/hooks/useChat"
import { Answer, Sources } from "@/components/answer"
import { Prompt } from "@/components/prompt"
import { Failed, Loading } from "@/components/states"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker"
import { Message, MessageContent } from "@/components/ui/message"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller"
import { Spinner } from "@/components/ui/spinner"
import type { Turn } from "@/hooks/useChat"

export function Chat() {
  const { projectid = "", conversationid } = useParams()
  const stored = useConversation(conversationid)

  if (conversationid && stored.isPending) return <Loading label="Loading conversation" />
  if (conversationid && stored.error)
    return (
      <div className="p-6">
        <Failed title="Conversation not found" failure={stored.error} />
      </div>
    )

  return (
    // Remounting on a thread change is what resets the transcript; there is no reset to write.
    <Thread
      key={conversationid ?? "new"}
      projectid={projectid}
      conversationid={conversationid}
      initial={stored.data ? toturns(stored.data) : []}
    />
  )
}

function Thread({
  projectid,
  conversationid,
  initial,
}: {
  projectid: string
  conversationid: string | undefined
  initial: Turn[]
}) {
  const navigate = useNavigate()
  const docs = useDocuments(projectid)
  const upload = useUpload(projectid)
  const started = useCallback(
    (id: string) => navigate(`/projects/${projectid}/c/${id}`, { replace: true }),
    [navigate, projectid],
  )
  const { turns, streaming, error, ask } = useChat(projectid, conversationid, initial, started)

  // Stored citations carry a document id; the live ones carry the name. This covers both.
  const names = useMemo(
    () => new Map(docs.data?.map((doc) => [doc.id, doc.filename])),
    [docs.data],
  )
  const indexing = docs.data?.filter(
    (doc) => doc.state === "uploaded" || doc.state === "processing",
  ).length

  return (
    <>
      <MessageScrollerProvider autoScroll defaultScrollPosition="end">
        <MessageScroller className="min-h-0 flex-1">
          <MessageScrollerViewport aria-label="Conversation">
            <MessageScrollerContent className="mx-auto w-full max-w-3xl px-4 py-6">
              {turns.length === 0 && (
                <Empty>
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <MessagesSquare />
                    </EmptyMedia>
                    <EmptyTitle>Ask about this project</EmptyTitle>
                    <EmptyDescription>
                      {docs.data?.length
                        ? "Answers come only from the documents you uploaded."
                        : "Upload a document first — there is nothing to answer from yet."}
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
              {turns.map((turn) => (
                <MessageScrollerItem key={turn.id} messageId={turn.id}>
                  <Message align={turn.role === "user" ? "end" : "start"}>
                    <MessageContent>
                      <Bubble
                        align={turn.role === "user" ? "end" : "start"}
                        variant={turn.role === "user" ? "default" : "ghost"}
                      >
                        <BubbleContent>
                          {turn.role === "user" ? (
                            turn.content
                          ) : turn.content ? (
                            <Answer content={turn.content} />
                          ) : (
                            streaming && (
                              <Marker>
                                <MarkerIcon>
                                  <Spinner />
                                </MarkerIcon>
                                <MarkerContent>Reading the documents</MarkerContent>
                              </Marker>
                            )
                          )}
                        </BubbleContent>
                      </Bubble>
                      {turn.role === "assistant" && (
                        <Sources sources={turn.citations} names={names} />
                      )}
                    </MessageContent>
                  </Message>
                </MessageScrollerItem>
              ))}
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>

      <div className="mx-auto flex w-full max-w-3xl shrink-0 flex-col gap-2 px-4 pb-4">
        {error && <Failed title="The answer stopped" failure={new Error(error)} />}
        {upload.error && <Failed title="Upload rejected" failure={upload.error} />}
        {!!indexing && (
          <Marker>
            <MarkerIcon>
              <Spinner />
            </MarkerIcon>
            <MarkerContent>
              Indexing {indexing} {indexing === 1 ? "document" : "documents"}
            </MarkerContent>
          </Marker>
        )}
        <Prompt busy={streaming} onsend={ask} onattach={(file) => upload.mutate(file)} />
      </div>
    </>
  )
}
