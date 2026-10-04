import { useSyncExternalStore } from "react"

const query = "(max-width: 767px)"

// Whether the screen is phone-sized
export const useMobile = () =>
  useSyncExternalStore(
    (listener) => {
      const media = matchMedia(query)
      media.addEventListener("change", listener)
      return () => media.removeEventListener("change", listener)
    },
    () => matchMedia(query).matches,
  )
