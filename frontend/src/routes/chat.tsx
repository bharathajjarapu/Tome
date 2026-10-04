import { lazy, Suspense, useCallback, useMemo, useState } from "react"
import { Link, useNavigate, useOutletContext, useParams } from "react-router"

import { indexing, useConversation, useDocuments, type Project } from "@/api/queries"
import { toturns, useChat, type Turn } from "@/hooks/chat"
import { Prompt } from "@/components/prompt"
import { Sources } from "@/components/sources"
import { Failed, Loading } from "@/components/states"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import { Button, buttonVariants } from "@/components/ui/button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Message, MessageContent } from "@/components/ui/message"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/scroller"

// Markdown pulls in a syntax highlighter, so it loads after first paint
const Answer = lazy(() => import("@/components/answer"))

const suggestions = [
  "Summarize the key points",
  "What decisions were made?",
  "List the open risks",
  "What are the next steps?",
]

export function Chat() {
  const { projectid = "", conversationid } = useParams()
  const stored = useConversation(conversationid)

  if (conversationid && stored.isPending)
    return (
      <div className="pt-14">
        <Loading label="Loading" />
      </div>
    )
  if (conversationid && stored.error)
    return (
      <div className="p-6 pt-16">
        <Failed title="Not found" failure={stored.error} />
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
  const project = useOutletContext<Project>()
  const docs = useDocuments(projectid)
  const [question, setquestion] = useState("")
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
  const ready = docs.data?.filter((doc) => doc.state === "indexed").length ?? 0
  const queued = docs.data?.filter(indexing).length ?? 0
  const empty = turns.length === 0

  function send() {
    if (!question.trim() || streaming) return
    ask(question.trim())
    setquestion("")
  }

  const composer = (
    <div className="flex w-full flex-col gap-2">
      {error && <Failed title="Failed" failure={new Error(error)} />}
      <Prompt value={question} onchange={setquestion} busy={streaming} tall={empty} onsend={send} />
    </div>
  )

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {empty ? (
        <div className="absolute inset-0 overflow-y-auto p-4 pt-16">
          <Empty className="h-full">
            <EmptyHeader>
              <EmptyTitle className="text-3xl">{project.name}</EmptyTitle>
              <EmptyDescription>
                {ready ? `${ready} ${ready === 1 ? "document" : "documents"}` : queued ? "Indexing…" : "No documents yet"}
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent className="max-w-2xl">
              {composer}
              {ready ? (
                <div className="grid w-full gap-2 sm:grid-cols-2">
                  {suggestions.map((text) => (
                    <Button key={text} variant="outline" className="h-auto justify-start py-2 text-left whitespace-normal" onClick={() => setquestion(text)}>
                      {text}
                    </Button>
                  ))}
                </div>
              ) : (
                <Link to={`/projects/${projectid}/documents`} className={buttonVariants({ variant: "outline" })}>
                  {queued ? "Indexing" : "Add documents"}
                </Link>
              )}
            </EmptyContent>
          </Empty>
        </div>
      ) : (
        <>
          <MessageScrollerProvider autoScroll defaultScrollPosition="end">
            <MessageScroller className="absolute inset-0">
              <MessageScrollerViewport aria-label="Conversation" className="fade">
                <MessageScrollerContent className="mx-auto w-full max-w-3xl px-4 pt-16 pb-28">
                  {turns.map((turn) => (
                    <MessageScrollerItem key={turn.id} messageId={turn.id}>
                      <Message align={turn.role === "user" ? "end" : "start"}>
                        <MessageContent>
                          <Bubble align={turn.role === "user" ? "end" : "start"} variant={turn.role === "user" ? "secondary" : "ghost"}>
                            <BubbleContent className="text-base">
                              {turn.role === "user" ? (
                                <span className="whitespace-pre-wrap">{turn.content}</span>
                              ) : turn.content ? (
                                <Suspense fallback={<p className="whitespace-pre-wrap">{turn.content}</p>}>
                                  <Answer content={turn.content} />
                                </Suspense>
                              ) : (
                                streaming && <span className="shimmer">Reading…</span>
                              )}
                            </BubbleContent>
                          </Bubble>
                          {turn.role === "assistant" && <Sources sources={turn.citations} names={names} />}
                        </MessageContent>
                      </Message>
                    </MessageScrollerItem>
                  ))}
                </MessageScrollerContent>
              </MessageScrollerViewport>
              <MessageScrollerButton className="bottom-28!" />
            </MessageScroller>
          </MessageScrollerProvider>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 px-4 pb-4">
            <div className="pointer-events-auto mx-auto max-w-3xl">{composer}</div>
          </div>
        </>
      )}
    </div>
  )
}
