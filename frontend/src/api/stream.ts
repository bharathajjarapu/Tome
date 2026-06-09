/**
 * Server-Sent Events over `fetch`. Not `EventSource`: it cannot set headers, so authenticating it
 * would put the token in the query string, where it lands in server logs and browser history.
 */

import { headers, toerror, url } from "@/api/client"

export type Frame = { event: string; data: string }

/** Parse one frame. Returns null for the keep-alives and comments that carry no data. */
export function parse(frame: string): Frame | null {
  let event = "message"
  const data: string[] = []
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim()
    else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""))
  }
  return data.length ? { event, data: data.join("\n") } : null
}

/** Frames from a byte stream, whatever the chunk boundaries happen to be. */
export async function* frames(body: ReadableStream<Uint8Array>): AsyncGenerator<Frame> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n")
      let end = buffer.indexOf("\n\n")
      while (end !== -1) {
        const frame = parse(buffer.slice(0, end))
        buffer = buffer.slice(end + 2)
        if (frame) yield frame
        end = buffer.indexOf("\n\n")
      }
    }
  } finally {
    reader.cancel().catch(() => {})
  }
}

export async function* sse(path: string, signal: AbortSignal): AsyncGenerator<Frame> {
  const res = await fetch(url(path), { headers: headers(), signal })
  if (!res.ok || !res.body) throw await toerror(res)
  yield* frames(res.body)
}
