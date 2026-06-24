"""FastAPI app entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import alerts, auth, chat, devices, scans
from .core.config import get_settings
from .core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AssetIA API",
    version="0.1.0",
    description="Inventario inteligente de TI com agente LLM (Claude).",
    lifespan=lifespan,
)

s = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=s.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])


@app.get("/")
def root():
    return {
        "app": "AssetIA",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "ok",
    }


@app.get("/api/saude")
def saude():
    return {"status": "ok"}
