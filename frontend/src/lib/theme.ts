import { useSyncExternalStore } from "react"

const KEY = "tome.theme"
const system = matchMedia("(prefers-color-scheme: dark)")
const listeners = new Set<() => void>()

// A saved choice wins; otherwise the system preference decides
const saved = () => localStorage.getItem(KEY)
const isdark = () => document.documentElement.classList.contains("dark")

function paint(dark: boolean) {
  document.documentElement.classList.toggle("dark", dark)
  for (const listener of listeners) listener()
}

// Applies the theme before first render and follows the system until a choice is saved
export function inittheme() {
  const choice = saved()
  paint(choice ? choice === "dark" : system.matches)
  system.addEventListener("change", () => saved() || paint(system.matches))
}

// Flips the theme, crossfading the page where the browser supports it
export function toggletheme() {
  const dark = !isdark()
  localStorage.setItem(KEY, dark ? "dark" : "light")
  if (document.startViewTransition) document.startViewTransition(() => paint(dark))
  else paint(dark)
}

export const useDark = () =>
  useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    isdark,
  )
