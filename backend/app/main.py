from fastapi import FastAPI

from app.api import auth, chat, documents, health, projects

app = FastAPI(title="PKA")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(chat.router)
