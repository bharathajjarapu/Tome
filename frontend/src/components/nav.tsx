import { HugeiconsIcon } from "@hugeicons/react"
import { Add01Icon, ArrowLeft02Icon, File02Icon, Logout01Icon } from "@hugeicons/core-free-icons"
import { Link, NavLink } from "react-router"

import { useConversations } from "@/api/queries"
import { useAuth } from "@/auth"
import { Loading } from "@/components/states"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"

// Sidebar for one project: new chat, documents, past conversations
export function Nav({ projectid }: { projectid: string }) {
  const conversations = useConversations(projectid)
  const { signout } = useAuth()
  const { dismiss } = useSidebar()
  const base = `/projects/${projectid}`

  // Row with an icon and label that links somewhere
  const link = (icon: typeof Add01Icon, label: string, to: string, end = false) => (
    <SidebarMenuItem>
      <SidebarMenuButton render={<NavLink to={to} end={end} />}>
        <HugeiconsIcon icon={icon} /> {label}
      </SidebarMenuButton>
    </SidebarMenuItem>
  )

  return (
    // A tapped link closes the mobile drawer
    <Sidebar onClick={(event) => event.target instanceof Element && event.target.closest("a") && dismiss()}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton className="h-auto text-lg font-semibold" render={<Link to="/" />}>
              Tome
            </SidebarMenuButton>
          </SidebarMenuItem>
          {link(Add01Icon, "New chat", base, true)}
          {link(File02Icon, "Documents", `${base}/documents`)}
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Conversations</SidebarGroupLabel>
          {conversations.isPending && <Loading label="Loading" />}
          {conversations.data?.length === 0 && <p className="px-2 text-xs text-muted-foreground">Nothing asked yet.</p>}
          <SidebarMenu>
            {conversations.data?.map((conversation) => (
              <SidebarMenuItem key={conversation.id}>
                <SidebarMenuButton render={<NavLink to={`${base}/c/${conversation.id}`} />}>
                  <span>{conversation.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          {link(ArrowLeft02Icon, "All projects", "/", true)}
          <SidebarMenuItem>
            <SidebarMenuButton onClick={signout}>
              <HugeiconsIcon icon={Logout01Icon} /> Sign out
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
