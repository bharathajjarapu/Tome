import { expect, test } from "vitest"

import { frames, parse } from "@/api/stream"

const stream = (chunks: string[]) =>
  new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk))
      controller.close()
    },
  })

const collect = async (chunks: string[]) => {
  const seen = []
  for await (const frame of frames(stream(chunks))) seen.push(frame)
  return seen
}

test("a frame split across chunk boundaries still arrives whole", async () => {
  const seen = await collect(['event: token\nda', 'ta: {"text":"hel', 'lo"}\n\n'])
  expect(seen).toEqual([{ event: "token", data: '{"text":"hello"}' }])
})

test("several frames in one chunk arrive in order", async () => {
  const seen = await collect(["event: token\ndata: a\n\nevent: token\ndata: b\n\n"])
  expect(seen.map((frame) => frame.data)).toEqual(["a", "b"])
})

test("multi-line data is joined with newlines", async () => {
  const seen = await collect(["event: token\ndata: first\ndata: second\n\n"])
  expect(seen[0].data).toBe("first\nsecond")
})

test("an error event is delivered like any other", async () => {
  const seen = await collect(['event: error\ndata: {"detail":"broken"}\n\n'])
  expect(seen[0]).toEqual({ event: "error", data: '{"detail":"broken"}' })
})

test("a stream ending without message_end yields only what arrived", async () => {
  const seen = await collect(["event: message_start\ndata: {}\n\nevent: token\ndata: half"])
  expect(seen.map((frame) => frame.event)).toEqual(["message_start"])
})

test("breaking out mid-stream cancels the reader", async () => {
  const body = stream(["event: token\ndata: a\n\nevent: token\ndata: b\n\n"])
  for await (const frame of frames(body)) {
    expect(frame.data).toBe("a")
    break
  }
  expect(body.locked).toBe(true)
})

test("a comment or keep-alive carries no data and is skipped", () => {
  expect(parse(": keep-alive")).toBeNull()
})
