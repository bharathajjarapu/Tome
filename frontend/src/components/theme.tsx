import { HugeiconsIcon } from "@hugeicons/react"
import { Moon02Icon, Sun03Icon } from "@hugeicons/core-free-icons"

import { Button } from "@/components/ui/button"
import { toggletheme, useDark } from "@/lib/theme"

// Switches between light and dark
export function ThemeToggle({ className }: { className?: string }) {
  const dark = useDark()
  return (
    <Button variant="ghost" size="icon-lg" className={className} aria-label={dark ? "Light mode" : "Dark mode"} onClick={toggletheme}>
      <HugeiconsIcon icon={dark ? Sun03Icon : Moon02Icon} />
    </Button>
  )
}
