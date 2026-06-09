import { useSyncExternalStore } from "react"
import { Navigate, Outlet } from "react-router"

import { gettoken, settoken, subscribe } from "@/api/token"

/** ponytail: a module store, not a context. Same result, no provider to thread through the tree. */
export function useAuth() {
  const token = useSyncExternalStore(subscribe, gettoken, gettoken)
  return { token, signin: settoken, signout: () => settoken(null) }
}

export function RequireAuth() {
  const { token } = useAuth()
  return token ? <Outlet /> : <Navigate to="/login" replace />
}
