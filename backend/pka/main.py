from fastapi import FastAPI

from pka.api import auth, chat, conversations, documents, health, projects
from pka.core import errors, log

log.setup()

app = FastAPI(title="PKA")
errors.install(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)
