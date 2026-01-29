from fastapi import FastAPI

from app.api import auth, health

app = FastAPI(title="PKA")

app.include_router(health.router)
app.include_router(auth.router)
