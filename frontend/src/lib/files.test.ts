import { describe, expect, it } from "vitest"

import { ago, extension, MAX_BYTES, refusal } from "@/lib/files"

describe("refusal", () => {
  it("accepts every supported type, whatever the case", () => {
    for (const name of ["a.pdf", "A.DOCX", "notes.md", "data.csv", "book.epub", "x.y.txt"])
      expect(refusal({ name, size: 10 })).toBeNull()
  })

  it("refuses unknown or missing extensions", () => {
    expect(refusal({ name: "run.exe", size: 10 })).toBe("Unsupported type")
    expect(refusal({ name: "pdf", size: 10 })).toBe("Unsupported type")
    expect(refusal({ name: "noext", size: 10 })).toBe("Unsupported type")
  })

  it("refuses files over the limit but takes one exactly at it", () => {
    expect(refusal({ name: "a.pdf", size: MAX_BYTES })).toBeNull()
    expect(refusal({ name: "a.pdf", size: MAX_BYTES + 1 })).toBe("Over 25 MB")
  })
})

describe("extension", () => {
  it("is lowercase and empty when there is none", () => {
    expect(extension("Report.PDF")).toBe("pdf")
    expect(extension("archive.tar.gz")).toBe("gz")
  })
})

describe("ago", () => {
  const now = Date.parse("2026-10-04T12:00:00Z")
  it("reads naturally at each scale", () => {
    expect(ago("2026-10-04T11:59:40Z", now)).toBe("just now")
    expect(ago("2026-10-04T11:55:00Z", now)).toBe("5 minutes ago")
    expect(ago("2026-10-04T10:00:00Z", now)).toBe("2 hours ago")
    expect(ago("2026-10-03T12:00:00Z", now)).toBe("yesterday")
    expect(ago("2026-09-30T12:00:00Z", now)).toBe("4 days ago")
  })
})
