import { useState } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import { Add01Icon } from "@hugeicons/core-free-icons"
import { Link, useNavigate } from "react-router"

import { useCreateProject, useProjects } from "@/api/queries"
import { useAuth } from "@/auth"
import { Failed, Loading } from "@/components/states"
import { ThemeToggle } from "@/components/theme"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Input } from "@/components/ui/input"

export function Projects() {
  const projects = useProjects()
  const create = useCreateProject()
  const { signout } = useAuth()
  const navigate = useNavigate()
  const [name, setname] = useState("")

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    create.mutate(name.trim(), {
      onSuccess: (project) => navigate(`/projects/${project.id}`),
    })
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <div className="flex items-center gap-1">
          <Button variant="ghost" onClick={signout}>
            Sign out
          </Button>
          <ThemeToggle />
        </div>
      </header>

      <form className="flex gap-2" onSubmit={submit}>
        <Input
          aria-label="New project name"
          placeholder="New project"
          value={name}
          onChange={(event) => setname(event.target.value)}
        />
        <Button type="submit" disabled={!name.trim() || create.isPending}>
          <HugeiconsIcon icon={Add01Icon} data-icon="inline-start" /> Create
        </Button>
      </form>
      {create.error && <Failed title="Create failed" failure={create.error} />}

      {projects.isPending && <Loading label="Loading" />}
      {projects.error && <Failed title="Load failed" failure={projects.error} />}

      {projects.data?.length === 0 && (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>No projects yet</EmptyTitle>
          </EmptyHeader>
        </Empty>
      )}

      <ul className="flex flex-col gap-2">
        {projects.data?.map((project) => (
          <li key={project.id}>
            <Link
              to={`/projects/${project.id}`}
              className="block rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <Card className="hover:bg-muted/50">
                <CardHeader>
                  <CardTitle>{project.name}</CardTitle>
                </CardHeader>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  )
}
