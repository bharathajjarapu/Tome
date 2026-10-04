import { useState } from "react"
import { useNavigate } from "react-router"

import { ApiError, post } from "@/api/client"
import type { Schemas } from "@/api/client"
import { useAuth } from "@/auth"
import { Failed } from "@/components/states"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { ThemeToggle } from "@/components/theme"

export function Login() {
  const { signin } = useAuth()
  const navigate = useNavigate()
  const [registering, setregistering] = useState(false)
  const [email, setemail] = useState("")
  const [password, setpassword] = useState("")
  const [busy, setbusy] = useState(false)
  const [failure, setfailure] = useState<ApiError | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setbusy(true)
    setfailure(null)
    try {
      const credentials = { email, password }
      if (registering) await post<Schemas["UserOut"]>("/auth/register", credentials)
      const { access_token } = await post<Schemas["TokenOut"]>("/auth/login", credentials)
      signin(access_token)
      navigate("/", { replace: true })
    } catch (error) {
      setfailure(error instanceof ApiError ? error : new ApiError(0, "network", "Cannot reach the server"))
    } finally {
      setbusy(false)
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center p-6">
      <ThemeToggle className="absolute top-4 right-4" />
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">{registering ? "Create account" : "Tome"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setemail(event.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete={registering ? "new-password" : "current-password"}
                value={password}
                onChange={(event) => setpassword(event.target.value)}
              />
            </div>
            {failure && <Failed title="Failed" failure={failure} />}
            <Button type="submit" disabled={busy}>
              {busy && <Spinner />}
              {registering ? "Create account" : "Sign in"}
            </Button>
            <Button
              type="button"
              variant="link"
              onClick={() => {
                setregistering(!registering)
                setfailure(null)
              }}
            >
              {registering ? "Sign in" : "Create account"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
