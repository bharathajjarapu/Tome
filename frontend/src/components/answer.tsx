import { Streamdown } from "streamdown"

import type { Source } from "@/api/queries"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

/** The sources an answer was built from, folded away until asked for. */
export function Sources({
  sources,
  names,
}: {
  sources: Source[]
  names: Map<string, string>
}) {
  if (sources.length === 0) return null
  return (
    <Collapsible>
      <CollapsibleTrigger
        render={<Button variant="ghost" size="xs" className="text-muted-foreground" />}
      >
        {sources.length} {sources.length === 1 ? "source" : "sources"}
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1 flex flex-col gap-2">
        {sources.map((source, position) => (
          <figure
            key={`${source.chunk_id}-${position}`}
            className="rounded-lg border bg-card px-3 py-2 text-xs"
          >
            <figcaption className="font-medium">
              {source.document_name ?? names.get(source.document_id) ?? "Document"}
              {source.section ? ` — ${source.section}` : ""}
              {source.page !== null && source.page !== undefined ? ` — page ${source.page}` : ""}
            </figcaption>
            <blockquote className="mt-1 text-muted-foreground">{source.snippet}</blockquote>
          </figure>
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}

/** Markdown that renders correctly while it is still half-written. */
export function Answer({ content }: { content: string }) {
  return (
    // Images are dropped: the answer is model output over uploaded documents, and an injected
    // ![](https://…?q=secret) would be fetched by the browser without a click.
    <Streamdown mode="streaming" className="space-y-3" components={{ img: () => null }}>
      {content}
    </Streamdown>
  )
}
