import { ArrowLeft, FileText, MessageSquarePlus } from "lucide-react"
import { Link, NavLink, Outlet, useParams } from "react-router"

import { useConversations, useProject } from "@/api/queries"
import { useAuth } from "@/auth"
import { Failed, Loading } from "@/components/states"
import { Button } from "@/components/ui/button"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"

export function Project() {
  const { projectid = "" } = useParams()
  const project = useProject(projectid)
  const conversations = useConversations(projectid)
  const { signout } = useAuth()

  if (project.isPending) return <Loading label="Loading project" />
  if (project.error)
    return (
      <div className="p-6">
        <Failed title="Project not found" failure={project.error} />
        <Button variant="link" render={<Link to="/" />}>
          Back to projects
        </Button>
      </div>
    )

  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton render={<Link to="/" />}>
                <ArrowLeft />
                <span className="truncate font-medium">{project.data.name}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton render={<NavLink to={`/projects/${projectid}`} end />}>
                <MessageSquarePlus />
                New chat
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton render={<NavLink to={`/projects/${projectid}/documents`} />}>
                <FileText />
                Documents
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Conversations</SidebarGroupLabel>
            <SidebarGroupContent>
              {conversations.isPending && <Loading label="Loading" />}
              {conversations.data?.length === 0 && (
                <p className="px-2 text-xs text-muted-foreground">Nothing asked yet.</p>
              )}
              <SidebarMenu>
                {conversations.data?.map((conversation) => (
                  <SidebarMenuItem key={conversation.id}>
                    <SidebarMenuButton
                      render={<NavLink to={`/projects/${projectid}/c/${conversation.id}`} />}
                    >
                      <span className="truncate">{conversation.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter>
          <Button variant="ghost" size="sm" onClick={signout}>
            Sign out
          </Button>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="flex h-svh min-h-0 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
          <SidebarTrigger />
          <span className="truncate text-sm font-medium">{project.data.name}</span>
        </header>
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )
}
