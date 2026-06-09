import { expect, test } from "vitest"

import { ApiError, toerror } from "@/api/client"
import { gettoken, settoken } from "@/api/token"

const backend = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } })

test("the backend's error shape becomes an ApiError", async () => {
  const failure = await toerror(
    backend(409, { error: { code: "conflict", message: "Email already registered" } }),
  )
  expect(failure).toBeInstanceOf(ApiError)
  expect(failure.status).toBe(409)
  expect(failure.code).toBe("conflict")
  expect(failure.message).toBe("Email already registered")
})

test("a body that is not that shape still becomes an ApiError", async () => {
  const failure = await toerror(new Response("<html>gateway</html>", { status: 502 }))
  expect(failure).toBeInstanceOf(ApiError)
  expect(failure.status).toBe(502)
  expect(failure.message.length).toBeGreaterThan(0)
})

test("a 401 clears the stored token", async () => {
  settoken("stale-token")
  await toerror(backend(401, { error: { code: "unauthorized", message: "Not authenticated" } }))
  expect(gettoken()).toBeNull()
})
