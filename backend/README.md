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
`citation` event per source, then `message_end`. A question the documents do not cover is refused
without calling the LLM. Reopen the whole exchange later with
`GET /conversations/{conversation_id}`.

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

## Layout

```
pka/api/        routers, thin
pka/services/   business logic
pka/ingestion/  parse, chunk
pka/rag/        index, retrieve, rerank, context, prompts, generate
pka/core/       settings, database, security, dependencies, errors, logging
pka/worker.py   the ingestion worker
pka/storage.py  files on disk
```

Three pieces are meant to be swapped, each at one call site: the parser (`ingestion/parse.py`),
the reranker (`rag/rerank.py`), and the LLM (`rag/generate.py`).
