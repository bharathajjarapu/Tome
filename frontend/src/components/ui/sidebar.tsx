import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ComponentProps } from "react"
import { Dialog } from "@base-ui/react/dialog"
import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { HugeiconsIcon } from "@hugeicons/react"
import { SidebarLeftIcon } from "@hugeicons/core-free-icons"

import { Button } from "@/components/ui/button"
import { useMobile } from "@/hooks/mobile"
import { cn } from "@/lib/utils"

type Context = { open: boolean; toggle: () => void; setOpen: (open: boolean) => void; dismiss: () => void }

const SidebarContext = createContext<Context | null>(null)

// Reads the sidebar state from the nearest provider
export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) throw new Error("useSidebar must be used within a SidebarProvider.")
  return context
}

// Holds open state for the desktop sidebar and the mobile drawer, toggled with Ctrl+B
export function SidebarProvider({ defaultOpen = true, className, ...props }: ComponentProps<"div"> & { defaultOpen?: boolean }) {
  const mobile = useMobile()
  const [desktop, setDesktop] = useState(defaultOpen)
  const [drawer, setDrawer] = useState(false)
  const toggle = useCallback(() => (mobile ? setDrawer : setDesktop)((open) => !open), [mobile])
  const context = useMemo(
    () => ({ open: mobile ? drawer : desktop, toggle, setOpen: mobile ? setDrawer : setDesktop, dismiss: () => setDrawer(false) }),
    [mobile, drawer, desktop, toggle],
  )

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "b" || !(event.metaKey || event.ctrlKey)) return
      event.preventDefault()
      toggle()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [toggle])

  return (
    <SidebarContext.Provider value={context}>
      <div className={cn("flex min-h-svh w-full", className)} {...props} />
    </SidebarContext.Provider>
  )
}

// Fixed panel on desktop, slide-over drawer on mobile
export function Sidebar({ children, ...props }: ComponentProps<"div">) {
  const { open, setOpen } = useSidebar()
  const mobile = useMobile()
  const panel = "flex flex-col bg-sidebar text-sidebar-foreground"

  if (mobile) {
    return (
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/10 transition-opacity data-ending-style:opacity-0 data-starting-style:opacity-0" />
          <Dialog.Popup
            className={cn(panel, "fixed inset-y-0 left-0 z-50 w-72 shadow-lg transition duration-200 data-ending-style:-translate-x-10 data-ending-style:opacity-0 data-starting-style:-translate-x-10 data-starting-style:opacity-0")}
            {...props}
          >
            <Dialog.Title className="sr-only">Navigation</Dialog.Title>
            {children}
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    )
  }

  return (
    <>
      <div className={cn("w-64 shrink-0 transition-[width] duration-200 ease-linear", !open && "w-0")} />
      <div
        inert={!open}
        className={cn(panel, "fixed inset-y-0 left-0 z-10 w-64 border-r transition-[left] duration-200 ease-linear", !open && "-left-64")}
        {...props}
      >
        {children}
      </div>
    </>
  )
}

// Button that opens and closes the sidebar
export function SidebarTrigger(props: ComponentProps<typeof Button>) {
  const { toggle } = useSidebar()
  return (
    <Button variant="ghost" size="icon-sm" onClick={toggle} {...props}>
      <HugeiconsIcon icon={SidebarLeftIcon} />
      <span className="sr-only">Toggle sidebar</span>
    </Button>
  )
}

// Page area beside the sidebar
export const SidebarInset = ({ className, ...props }: ComponentProps<"main">) => (
  <main className={cn("relative flex w-full min-w-0 flex-1 flex-col bg-background", className)} {...props} />
)

export const SidebarHeader = ({ className, ...props }: ComponentProps<"div">) => <div className={cn("flex flex-col gap-2 p-2", className)} {...props} />

export const SidebarFooter = SidebarHeader

export const SidebarContent = ({ className, ...props }: ComponentProps<"div">) => (
  <div className={cn("flex min-h-0 flex-1 flex-col overflow-auto", className)} {...props} />
)

export const SidebarGroup = ({ className, ...props }: ComponentProps<"div">) => <div className={cn("flex w-full min-w-0 flex-col p-2", className)} {...props} />

export const SidebarGroupLabel = ({ className, ...props }: ComponentProps<"div">) => (
  <div className={cn("flex h-8 shrink-0 items-center px-2 text-xs font-medium text-sidebar-foreground/70", className)} {...props} />
)

export const SidebarMenu = ({ className, ...props }: ComponentProps<"ul">) => <ul className={cn("flex w-full min-w-0 flex-col", className)} {...props} />

export const SidebarMenuItem = ({ className, ...props }: ComponentProps<"li">) => <li className={cn("group/item relative", className)} {...props} />

// Full-width row, a button or a router link through `render`, highlighted when active or on the current route
export function SidebarMenuButton({ isActive, className, render, ...props }: useRender.ComponentProps<"button"> & { isActive?: boolean }) {
  return useRender({
    defaultTagName: "button",
    props: mergeProps<"button">(
      {
        className: cn(
          "flex h-8 w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm outline-hidden hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring data-active:bg-sidebar-accent data-active:font-medium aria-[current=page]:bg-sidebar-accent aria-[current=page]:font-medium [&_svg]:size-4 [&_svg]:shrink-0 [&>span:last-child]:truncate",
          className,
        ),
      },
      props,
    ),
    render,
    state: { slot: "sidebar-menu-button", active: isActive },
  })
}
