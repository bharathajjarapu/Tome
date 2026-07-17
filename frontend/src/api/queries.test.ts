import { expect, test } from "vitest"

import { interval, type Doc } from "@/api/queries"

const NOW = Date.parse("2026-09-10T12:00:00Z")

const doc = (state: Doc["state"], secondsAgo: number): Doc => ({
  id: "d",
  filename: "book.epub",
  state,
  error: null,
  created_at: new Date(NOW - secondsAgo * 1000).toISOString(),
})

test("nothing to wait for means no polling", () => {
  expect(interval([], NOW)).toBe(false)
  expect(interval([doc("indexed", 5), doc("failed", 5)], NOW)).toBe(false)
})

test("a fresh upload is polled promptly", () => {
  expect(interval([doc("processing", 0)], NOW)).toBe(1500)
})

test("a long ingest backs off instead of hammering the server", () => {
  expect(interval([doc("processing", 60)], NOW)).toBe(7500)
  expect(interval([doc("processing", 3600)], NOW)).toBe(15000)
})

test("a new upload alongside a slow one restores prompt polling", () => {
  expect(interval([doc("processing", 3600), doc("uploaded", 0)], NOW)).toBe(1500)
})

test("a server clock ahead of the browser still polls at the fastest pace", () => {
  expect(interval([doc("processing", -60)], NOW)).toBe(1500)
})
