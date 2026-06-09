import { ApiError } from "@/api/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Spinner } from "@/components/ui/spinner"

export function Loading({ label }: { label: string }) {
  return (
    <div
      className="flex items-center gap-2 p-6 text-sm text-muted-foreground"
      role="status"
      aria-live="polite"
    >
      <Spinner /> {label}
    </div>
  )
}

export function say(failure: unknown): string {
  if (failure instanceof ApiError) return failure.message
  return failure instanceof Error ? failure.message : "Something went wrong"
}

export function Failed({ title, failure }: { title: string; failure: unknown }) {
  return (
    <Alert variant="destructive" role="alert">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{say(failure)}</AlertDescription>
    </Alert>
  )
}
