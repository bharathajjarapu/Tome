from fastapi import FastAPI

from app.api import health

app = FastAPI(title="PKA")

app.include_router(health.router)
