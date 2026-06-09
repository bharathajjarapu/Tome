/** The only place `fetch` is called. Owns the base URL, the bearer header and the error shape. */

import type { components } from "@/api/types"
import { gettoken, settoken } from "@/api/token"

export type Schemas = components["schemas"]

const BASE = import.meta.env.VITE_API_URL ?? "/api"

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
  }
}

export function url(path: string): string {
  return `${BASE}${path}`
}

export function headers(body?: BodyInit | null): Headers {
  const head = new Headers()
  const token = gettoken()
  if (token) head.set("authorization", `Bearer ${token}`)
  // FormData sets its own multipart boundary, so only JSON bodies are labelled here.
  if (typeof body === "string") head.set("content-type", "application/json")
  return head
}

/** Turn a failed response into an `ApiError`, whatever the body turns out to be. */
export async function toerror(res: Response): Promise<ApiError> {
  // An expired or rejected token is worthless everywhere, so drop it once, here.
  if (res.status === 401) settoken(null)
  const body: unknown = await res.json().catch(() => null)
  const error = (body as { error?: { code?: string; message?: string } } | null)?.error
  const message = error?.message || res.statusText || `Request failed (${res.status})`
  return new ApiError(res.status, error?.code ?? "error", message)
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(url(path), { ...init, headers: headers(init.body) })
  if (!res.ok) throw await toerror(res)
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

export function post<T>(path: string, body: unknown): Promise<T> {
  return api<T>(path, { method: "POST", body: JSON.stringify(body) })
}
