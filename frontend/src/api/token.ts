/** The access token, shared by the fetch client and the React tree. */

const KEY = "tome.token"
// Absent under Node, where the client's tests run.
const store = globalThis.localStorage as Storage | undefined

let token = store?.getItem(KEY) ?? null
const listeners = new Set<() => void>()

export function gettoken(): string | null {
  return token
}

export function settoken(next: string | null): void {
  token = next
  if (next) store?.setItem(KEY, next)
  else store?.removeItem(KEY)
  for (const listener of listeners) listener()
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
