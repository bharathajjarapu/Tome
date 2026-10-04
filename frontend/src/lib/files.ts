/** What the upload endpoint accepts, mirrored here so a bad file is refused before it is sent. */
const FORMATS = ["pdf", "docx", "doc", "odt", "rtf", "pptx", "xlsx", "epub", "csv", "md", "markdown", "txt"]
export const MAX_BYTES = 25_000_000

export const ACCEPT = FORMATS.map((format) => `.${format}`).join(",")

export const extension = (name: string) => name.split(".").pop()?.toLowerCase() ?? ""

/** Why a file cannot be uploaded, or null when it can. The server stays the authority. */
export function refusal(file: { name: string; size: number }): string | null {
  if (!supported(file.name)) return "Unsupported type"
  return file.size > MAX_BYTES ? "Over 25 MB" : null
}

const supported = (name: string) => name.includes(".") && FORMATS.includes(extension(name))

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" })
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86400],
  ["hour", 3600],
  ["minute", 60],
]

/** "2 hours ago", "yesterday", "just now". */
export function ago(iso: string, now = Date.now()): string {
  const seconds = (Date.parse(iso) - now) / 1000
  const [unit, size] = UNITS.find(([, size]) => Math.abs(seconds) >= size) ?? ["second", 0]
  return size ? rtf.format(Math.round(seconds / size), unit) : "just now"
}
