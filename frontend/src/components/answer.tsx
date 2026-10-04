import { Streamdown } from "streamdown"

/** Markdown that renders correctly while it is still half-written. Default export so the chat loads it after first paint. */
export default function Answer({ content }: { content: string }) {
  return (
    // Images are dropped: the answer is model output over uploaded documents, and an injected
    // ![](https://…?q=secret) would be fetched by the browser without a click.
    <Streamdown mode="streaming" className="space-y-3" components={{ img: () => null }}>
      {content}
    </Streamdown>
  )
}
