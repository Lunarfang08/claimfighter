#!/bin/bash
set -euo pipefail

STORAGE_DIR="${STORAGE_DIR:-/data/storage}"
UPLOADS_DIR="${UPLOADS_DIR:-/data/uploads}"
OLLAMA_MODELS="${OLLAMA_MODELS:-/data/ollama/models}"
MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"
PORT="${PORT:-8080}"

mkdir -p "$STORAGE_DIR" "$UPLOADS_DIR" "$OLLAMA_MODELS"
export OLLAMA_MODELS

if [ ! -f "$STORAGE_DIR/cases.json" ]; then
  echo '{"cases": []}' > "$STORAGE_DIR/cases.json"
fi

echo "Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama to be ready..."
for i in $(seq 1 90); do
  if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama is ready."
    break
  fi
  if [ "$i" -eq 90 ]; then
    echo "Ollama failed to start within 3 minutes."
    exit 1
  fi
  sleep 2
done

echo "Pulling model: $MODEL (skipped if already cached)..."
ollama pull "$MODEL"

echo "Starting FastAPI on port $PORT..."
cd /app/backend
exec uvicorn api.main:app --host 0.0.0.0 --port "$PORT"
