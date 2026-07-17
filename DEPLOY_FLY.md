# Fly.io Deployment Guide

Deploy the full stack as two Fly.io apps: **backend** (FastAPI + Ollama) and **frontend** (Next.js).

## Prerequisites

- [Fly.io account](https://fly.io/app/sign-up)
- [flyctl CLI](https://fly.io/docs/flyctl/install/) installed
- Logged in: `fly auth login`

## 1. Choose app names (optional)

Edit `fly.backend.toml` and `fly.frontend.toml` if you want custom app names. Defaults:

- Backend: `medical-insu-api`
- Frontend: `medical-insu-web`

App names must be globally unique on Fly.io.

## 2. Create the backend app + volume

From the **repo root**:

```bash
# Create the backend app (skip if already created)
fly apps create medical-insu-api

# Persistent storage for cases, uploads, and Ollama models (3 GB minimum)
fly volumes create medical_insu_data --region iad --size 3 -a medical-insu-api
```

> Use the same `primary_region` as in `fly.backend.toml` (`iad` by default).

## 3. Deploy the backend

```bash
fly deploy -c fly.backend.toml
```

**First deploy takes 5–10 minutes** — the container pulls the `qwen2.5:3b` model (~2 GB). Subsequent deploys reuse the cached model on the volume.

Check status:

```bash
fly status -a medical-insu-api
fly logs -a medical-insu-api
curl https://medical-insu-api.fly.dev/
```

Note your backend URL (e.g. `https://medical-insu-api.fly.dev`).

## 4. Deploy the frontend

Update the API URL in `fly.frontend.toml` under `[build.args]`:

```toml
[build.args]
  NEXT_PUBLIC_API_URL = 'https://medical-insu-api.fly.dev'
```

Then deploy:

```bash
fly apps create medical-insu-web
fly deploy -c fly.frontend.toml
```

Or pass the build arg inline:

```bash
fly deploy -c fly.frontend.toml \
  --build-arg NEXT_PUBLIC_API_URL=https://medical-insu-api.fly.dev
```

## 5. Configure CORS on the backend

Allow your frontend origin:

```bash
fly secrets set \
  ALLOWED_ORIGINS="https://medical-insu-web.fly.dev,http://localhost:3000" \
  -a medical-insu-api
```

Fly restarts the backend automatically after secrets change.

## 6. Verify end-to-end

1. Open `https://medical-insu-web.fly.dev`
2. Upload a sample from `data/samples/`
3. Run analysis and confirm the risk report loads

---

## Environment variables

### Backend (`medical-insu-api`)

| Variable | Default | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS origins |
| `STORAGE_DIR` | `/data/storage` | Case JSON storage (volume) |
| `UPLOADS_DIR` | `/data/uploads` | Uploaded documents (volume) |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434/v1` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Model to pull and use |
| `OLLAMA_MODELS` | `/data/ollama/models` | Model cache on volume |
| `PORT` | `8080` | Set automatically by Fly.io |

### Frontend (`medical-insu-web`)

| Variable | When | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Build time** | Backend URL baked into the client bundle |

> Changing the backend URL requires rebuilding and redeploying the frontend.

---

## Resource requirements

The backend runs Ollama + FastAPI and needs **at least 4 GB RAM** (configured in `fly.backend.toml`). The frontend runs on 512 MB.

Estimated cost: Fly.io bills by usage; the backend machine is the main cost driver due to memory and model storage.

---

## Useful commands

```bash
# Tail backend logs (watch model pull / API startup)
fly logs -a medical-insu-api

# SSH into backend machine
fly ssh console -a medical-insu-api

# Scale memory if Ollama OOMs
fly scale memory 4096 -a medical-insu-api

# Redeploy after code changes
fly deploy -c fly.backend.toml
fly deploy -c fly.frontend.toml
```

---

## Troubleshooting

**Backend health check fails on first deploy**
- Normal during model download. Grace period is 5 minutes; check `fly logs`.

**CORS errors in browser**
- Confirm `ALLOWED_ORIGINS` includes your exact frontend URL (with `https://`, no trailing slash).

**Processing fails with LLM error**
- SSH in and verify Ollama: `curl http://127.0.0.1:11434/api/tags`
- Confirm model exists: `ollama list`

**Frontend can't reach API**
- Rebuild frontend with correct `NEXT_PUBLIC_API_URL` build arg.
- Confirm backend is running: `curl https://medical-insu-api.fly.dev/`

**Out of memory**
- Increase to 6–8 GB: `fly scale memory 8192 -a medical-insu-api`

---

## Local development (unchanged)

```bash
# Terminal 1 — Ollama
ollama serve && ollama pull qwen2.5:3b

# Terminal 2 — Backend
cd backend && uvicorn api.main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend && npm run dev
```
