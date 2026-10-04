import { Link, Outlet, useParams } from "react-router"

import { useProject } from "@/api/queries"
import { Failed, Loading } from "@/components/states"
import { Header } from "@/components/header"
import { Nav } from "@/components/nav"
import { buttonVariants } from "@/components/ui/button"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export function Project() {
  const { projectid = "" } = useParams()
  const project = useProject(projectid)

  if (project.isPending) return <Loading label="Loading" />
  if (project.error)
    return (
      <div className="p-6">
        <Failed title="Not found" failure={project.error} />
        <Link to="/" className={buttonVariants({ variant: "link" })}>
          Back to projects
        </Link>
      </div>
    )

  return (
    <SidebarProvider>
      <Nav projectid={projectid} />
      <SidebarInset className="h-dvh">
        <Header />
        <Outlet context={project.data} />
      </SidebarInset>
    </SidebarProvider>
  )
}
