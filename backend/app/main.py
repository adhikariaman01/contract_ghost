"""Contract Ghost — FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.contract import router as contract_router
from app.services.vector_store import initialize_vector_store

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔍 Contract Ghost starting up...")
    initialize_vector_store()
    logger.info("✅ Vector store ready")
    yield
    logger.info("👋 Contract Ghost shutting down")


# ─── App ──────────────────────────────────────────────────────────────────────
settings = get_settings()

app = FastAPI(
    title="Contract Ghost API",
    description="Multi-agent system for detecting unenforceable contract clauses.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contract_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "contract-ghost"}
