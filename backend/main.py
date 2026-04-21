"""
FastAPI application entry point.

Mounts /api routers and serves the Next.js static export (frontend/out/) at /.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.rails_manager import get_rails_sync
from backend.routers.endpoints import router as endpoints_router
from backend.routers.guardrails import router as guardrails_router
from backend.routers.proxy import router as proxy_router
from backend.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly initialize NeMo Guardrails at startup so first request is fast.
    get_rails_sync()
    yield


app = FastAPI(title="NeMo Guardrails Proxy", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proxy_router)
app.include_router(endpoints_router)
app.include_router(guardrails_router)

# Serve the compiled Next.js static export — must come AFTER API routers.
frontend_dir = settings.frontend_dir
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "message": "NeMo Guardrails Proxy running. Frontend not built yet.",
            "api_docs": "/docs",
        }
