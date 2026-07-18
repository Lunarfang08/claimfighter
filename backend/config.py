"""Runtime configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path


def _split_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


_BACKEND_DIR = Path(__file__).parent

# Persistent storage (use /data/* on Fly.io with a mounted volume)
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", _BACKEND_DIR / "storage"))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", _BACKEND_DIR / "uploads"))

# CORS — comma-separated list, e.g. "http://localhost:3000,https://my-app.fly.dev"
ALLOWED_ORIGINS = _split_origins(
    os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
)

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Server (Fly.io sets PORT automatically)
PORT = int(os.getenv("PORT", "8000"))
