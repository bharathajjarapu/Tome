import { HugeiconsIcon } from "@hugeicons/react"
import { Add01Icon } from "@hugeicons/core-free-icons"
import { Link, useParams } from "react-router"

import { ThemeToggle } from "@/components/theme"
import { buttonVariants } from "@/components/ui/button"
import { SidebarTrigger } from "@/components/ui/sidebar"

// Top bar floating over the page
export function Header() {
  const { projectid } = useParams()
  return (
    <header className="pointer-events-none absolute inset-x-0 top-0 z-10 flex h-14 items-center gap-2 px-4 *:pointer-events-auto">
      <div className="flex items-center gap-1">
        <SidebarTrigger />
        <Link to={`/projects/${projectid}`} aria-label="New chat" className={buttonVariants({ variant: "ghost", size: "icon-sm" })}>
          <HugeiconsIcon icon={Add01Icon} />
        </Link>
      </div>
      <ThemeToggle className="ml-auto" />
    </header>
  )
}
