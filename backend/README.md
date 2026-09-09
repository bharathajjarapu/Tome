# Tome Backend

[← Tome](../README.md)

A local RAG assistant over a team's project documents. Upload files to a project, ask questions
about them, and get a streamed answer with citations. Nothing leaves the machine except the call
to the LLM.

## Architecture

```mermaid
flowchart LR
  Routes --> Services
  Services --> RAG
  Services --> Models
  Worker --> Ingestion
  Ingestion --> RAG
  RAG --> Qdrant
  Models --> Postgres
```

Routes are thin, and auth is a dependency (`CurrentUser`, `AccessibleProject`). Services hold the
logic. `rag/` and `ingestion/` are the only code that touches LlamaIndex. Postgres is the source of
truth; Qdrant only holds chunks.

### Ingestion

```mermaid
flowchart LR
  Upload --> Queue
  Queue --> Worker
  Worker --> Parse
  Parse --> Chunk
  Chunk --> Embed
  Embed --> Qdrant
```

- **Upload** stores the file and queues an `IngestionJob`, then returns. No parsing in the request.
- **Worker** claims jobs with `FOR UPDATE SKIP LOCKED`, so several can run side by side.
- **Parse** turns binaries into Markdown through AnyDoc; text files are decoded directly.
- **Chunk** splits by heading, then into 512-token sentence windows. Tables split by row and repeat
  their header in every chunk. Each chunk carries document name and section.
- **Embed** writes dense and sparse vectors in batches of 128.
- A failure drops the document's chunks and retries up to `MAX_ATTEMPTS`, then marks it `failed`.
- A job left `processing` past `STALE_MINUTES` lost its worker; it is claimed again and the crash
  counts as an attempt, so a file that kills the worker cannot loop forever.

### Retrieval

```mermaid
flowchart LR
  Question --> Condense
  Condense --> Dense
  Condense --> Sparse
  Dense --> Fusion
  Sparse --> Fusion
  Fusion --> Rerank
  Rerank --> LLM
```

| Step | Detail |
| --- | --- |
| Condense | Follow-ups rewritten into a standalone query; skipped on the first question |
| Dense | `nomic-embed-text-v1.5-Q`, 768 dims, 8k context, int8 |
| Sparse | `Qdrant/bm25`, exact terms such as codes and names |
| Fusion | Relative score fusion, equal weight, top 30 from each |
| Rerank | `ms-marco-MiniLM-L-6-v2` cross-encoder, keeps 6 |
| LLM | Answers from the numbered passages only, cites them, refuses when they fall short |

Every query filters on `team_id` and `project_id`, both indexed in Qdrant. `rag/store.py` holds the
only retriever and requires both ids, so an unscoped search cannot be built.

### Streaming

`POST /projects/{id}/chat` stores the question. `GET /projects/{id}/chat/stream` answers it as SSE:
`message_start`, `token`..., `citation`..., `message_end`. The answer and its citations are saved
once the stream ends. Failures send one `error` event with a generic message; details go to the log.
A question already answered returns 409, so a reload never pays for the same answer twice.

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Docker, for Postgres and Qdrant
- An API key for any OpenAI-compatible chat endpoint

## Setup

```bash
cd backend
uv sync
cp .env.example .env
```

Fill three values in `.env`; the rest of the file already points at the Docker services.

```
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
JWT_SECRET=$(openssl rand -hex 32)
```

Start Postgres and Qdrant from the repository root, then create the schema:

```bash
docker compose up -d postgres qdrant
cd backend && uv run alembic upgrade head
```

With Podman and no compose plugin, the same two services:

```bash
podman run -d --name tome-postgres -p 5432:5432 \
  -e POSTGRES_USER=tome -e POSTGRES_PASSWORD=tome -e POSTGRES_DB=tome docker.io/library/postgres:17-alpine
podman run -d --name tome-qdrant -p 6333:6333 docker.io/qdrant/qdrant:v1.12.4
```

## Run

Two processes. The API serves requests; the worker indexes uploads in the background.

```bash
uv run uvicorn tome.main:app --reload    # http://localhost:8000
uv run python -m tome.worker             # in a second terminal
```

`GET /health` answers `{"status": "ok"}`. The interactive API docs are at `/docs`.

In containers, `Dockerfile` builds one image that compose runs twice: `api` applies migrations and
serves, `worker` indexes. Both run as a non-root user and share the `uploads` and `models` volumes,
so the embedding and reranking models download once.

## Walkthrough

Register, log in, and keep the token:

```bash
curl -sX POST localhost:8000/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"sam@example.com","password":"correct-horse"}'

TOKEN=$(curl -sX POST localhost:8000/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"sam@example.com","password":"correct-horse"}' | jq -r .access_token)
```

Registration creates a personal team. Create a project in it:

```bash
PROJECT=$(curl -sX POST localhost:8000/projects \
  -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"name":"Handbook"}' | jq -r .id)
```

Upload a document. The request returns immediately; the worker does the work.

```bash
DOC=$(curl -sX POST localhost:8000/projects/$PROJECT/documents \
  -H "authorization: Bearer $TOKEN" -F file=@handbook.pdf | jq -r .id)

curl -s localhost:8000/documents/$DOC/status -H "authorization: Bearer $TOKEN"
```

Wait for `"state": "indexed"`, then ask a question. Asking and streaming are two calls, because
`EventSource` cannot send a POST.

```bash
MESSAGE=$(curl -sX POST localhost:8000/projects/$PROJECT/chat \
  -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"question":"How long are logs kept?"}' | jq -r .message_id)

curl -N "localhost:8000/projects/$PROJECT/chat/stream?message_id=$MESSAGE" \
  -H "authorization: Bearer $TOKEN"
```

The stream sends `message_start`, then one `token` event per fragment of the answer, then one
`citation` event per source, then `message_end`. A follow-up question is rewritten into a standalone
one using the conversation so far, so "and after that?" retrieves sensibly. A question the documents
do not cover is refused by the model, which has seen the passages, rather than by a score threshold.
Reopen the whole exchange later with `GET /conversations/{conversation_id}`.

## Tests and checks

```bash
uv run pytest
uv run ruff check .
uv run mypy tome
```

The suite runs against SQLite and an in-process Qdrant by default, so it needs no Docker. Point it
at the real services to run the same tests against them:

```bash
TEST_DATABASE_URL=postgresql+psycopg://tome:tome@localhost:5432/tome \
TEST_QDRANT_URL=http://localhost:6333 uv run pytest
```

Retrieval quality has its own suite, kept out of the default run because it downloads three
papers and embeds them. It scores hit rate, MRR and NDCG over a question set whose correct
source document is known, before and after reranking:

```bash
uv run pytest -m eval -s            # both suites
uv run pytest -m eval -s -k beir    # just the public benchmark
```

Two suites: our own questions over three papers, and a slice of SciFact from BEIR. Both cache
their corpus under `.eval-cache/`, which is not tracked.

Changing the embedding model leaves every stored vector stale and the wrong width. Drop the
collection and upload the documents again:

```bash
curl -X DELETE "$QDRANT_URL/collections/nodes"
```

## Layout

```
tome/api/       routers, thin
tome/services/  business logic
tome/ingestion/ parse, nodes
tome/rag/       store, rerank, llm, chat, prompts
tome/core/      settings, database, security, dependencies, errors, logging
tome/worker.py  the ingestion worker
tome/storage.py files on disk
```

Retrieval, reranking and generation are LlamaIndex: a hybrid Qdrant store, a cross-encoder node
postprocessor, and a `CondensePlusContextChatEngine`. Three pieces are meant to be swapped, each at
one call site: the parser (`ingestion/parse.py`), the reranker (`rag/rerank.py`), and the LLM
(`rag/llm.py`).

`rag/store.py` holds the only retriever, and it takes the team and project ids as required
arguments, so an unscoped one cannot be built.
