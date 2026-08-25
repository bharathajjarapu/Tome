# PKA Backend

A local RAG assistant over a team's project documents. Upload files to a project, ask questions
about them, and get a streamed answer with citations. Nothing leaves the machine except the call
to the LLM.

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
docker compose up -d
cd backend && uv run alembic upgrade head
```

With Podman and no compose plugin, the same two services:

```bash
podman run -d --name pka-postgres -p 5432:5432 \
  -e POSTGRES_USER=pka -e POSTGRES_PASSWORD=pka -e POSTGRES_DB=pka postgres:17-alpine
podman run -d --name pka-qdrant -p 6333:6333 qdrant/qdrant:v1.12.4
```

## Run

Two processes. The API serves requests; the worker indexes uploads in the background.

```bash
uv run uvicorn pka.main:app --reload     # http://localhost:8000
uv run python -m pka.worker              # in a second terminal
```

`GET /health` answers `{"status": "ok"}`. The interactive API docs are at `/docs`.

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
uv run mypy pka
```

The suite runs against SQLite and an in-process Qdrant by default, so it needs no Docker. Point it
at the real services to run the same tests against them:

```bash
TEST_DATABASE_URL=postgresql+psycopg://pka:pka@localhost:5432/pka \
TEST_QDRANT_URL=http://localhost:6333 uv run pytest
```

Retrieval quality has its own suite, kept out of the default run because it downloads three
papers and embeds them. It scores hit rate, MRR and NDCG over a question set whose correct
source document is known, before and after reranking:

```bash
uv run pytest -m eval -s
```

Changing the embedding model leaves every stored vector stale and the wrong width. Drop the
collection and upload the documents again:

```bash
curl -X DELETE "$QDRANT_URL/collections/nodes"
```

## Layout

```
pka/api/        routers, thin
pka/services/   business logic
pka/ingestion/  parse, nodes
pka/rag/        store, rerank, llm, chat, prompts
pka/core/       settings, database, security, dependencies, errors, logging
pka/worker.py   the ingestion worker
pka/storage.py  files on disk
```

Retrieval, reranking and generation are LlamaIndex: a hybrid Qdrant store, a cross-encoder node
postprocessor, and a `CondensePlusContextChatEngine`. Three pieces are meant to be swapped, each at
one call site: the parser (`ingestion/parse.py`), the reranker (`rag/rerank.py`), and the LLM
(`rag/llm.py`).

`rag/store.py` holds the only retriever, and it takes the team and project ids as required
arguments, so an unscoped one cannot be built.
