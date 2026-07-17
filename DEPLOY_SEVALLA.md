# Deploy on Sevalla

Your app needs **two** Sevalla resources:

| Part | Sevalla type | Why |
|---|---|---|
| Backend (FastAPI + LLM) | **Application** | Needs a running Python server |
| Frontend (Next.js) | **Application** (recommended) or Static site | Next.js App Router is not a plain static HTML site |

> **Do not finish the current "Create static site" form for the whole app.**  
> That screen only hosts frontend files. Your API will not run there.

---

## Before you deploy (required)

### 1. Get a free Groq API key (no card)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with email/GitHub
3. Create an API key

Sevalla free/hobby instances cannot run Ollama (needs ~4 GB RAM). Use Groq instead.

### 2. Push all code to GitHub

Your deploy configs and many changes are still **local only**. Also, `frontend` is currently a **git submodule** on GitHub — Sevalla may not see your Next.js files.

From the repo root:

```bash
# Fix frontend submodule → real folder (if needed)
git rm --cached frontend
# then add frontend files normally (do this carefully)

git add -A
git commit -m "Prepare Sevalla deploy: env-based LLM + Fly/Sevalla configs"
git push origin main
```

Confirm on GitHub that you can open files like:
- `backend/api/main.py`
- `frontend/package.json`
- `pipeline/llm_client.py`

---

## Step A — Deploy the backend (Application)

1. In Sevalla sidebar click **Applications** (not Static sites)
2. **Add application** → GitHub → `Lunarfang08/claimfighter` → branch `main`
3. Use these settings:

| Field | Value |
|---|---|
| Name | `claimfighter-api` |
| Build method | Nixpacks (default) |
| Build command | `pip install -e . && pip install -r backend/requirements.txt` |
| Start command | `cd backend && uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Instance | Smallest available (use free credits if offered) |

4. Environment variables:

| Key | Value |
|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:3000` (update after frontend URL exists) |
| `OLLAMA_BASE_URL` | `https://api.groq.com/openai/v1` |
| `OLLAMA_MODEL` | `llama-3.1-8b-instant` |
| `OPENAI_API_KEY` | your Groq API key |

5. Deploy, then open the Sevalla URL for the app. You should see:

```json
{"status":"healthy","service":"Medical Claim Fighter API","version":"1.0.0"}
```

Copy that URL (e.g. `https://claimfighter-api-xxxx.sevalla.app`).

---

## Step B — Deploy the frontend (Application)

Next.js with App Router works best as an **Application**, not a Static site.

1. **Applications** → Add application → same repo `claimfighter` → `main`
2. Settings:

| Field | Value |
|---|---|
| Name | `claimfighter-web` |
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Start command | `npm run start` |
| Node version | `20` or `lts` |

3. Environment variable (**build + runtime**):

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-BACKEND-URL` (from Step A, no trailing slash) |
| `PORT` | usually set by Sevalla automatically |

4. Deploy and open the frontend URL.

---

## Step C — Connect CORS

Back on the **backend** application, update:

```
ALLOWED_ORIGINS=https://YOUR-FRONTEND-URL,http://localhost:3000
```

Redeploy/restart the backend if needed.

---

## About the Static site form you’re on now

If you already filled it in, **cancel / don’t create it** for the API.

Static site fields (only if you later convert Next.js to a static export):

| Field | Value |
|---|---|
| Build site before publishing | **ON** |
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Publish directory | `out` (requires `output: 'export'` in `next.config`) |

Your app currently uses `output: 'standalone'`, so **Application hosting is the correct path**.

---

## Card / billing note

- **Static sites** on Sevalla: free tier (bandwidth/build minutes)
- **Applications** (needed for FastAPI + Next.js server): often need billing method / use signup credits (`$50` is commonly advertised)

If Sevalla asks for a card for Applications, same problem as Fly — then use:

- Frontend → **Vercel** (free, no card)
- Backend → **Render** free web service (no card) + Groq

---

## Quick test checklist

1. Backend `/` returns healthy JSON  
2. Frontend loads  
3. Upload `data/samples/denial_medical_necessity_emergency.txt`  
4. Processing completes (Groq key must be set)  
5. Risk report + appeal letter appear  

---

## If deploy fails

| Symptom | Fix |
|---|---|
| `frontend/package.json` not found | Frontend still a git submodule — push real frontend files |
| LLM / 401 errors | Check `OPENAI_API_KEY` + `OLLAMA_BASE_URL` on backend |
| CORS errors in browser | Update `ALLOWED_ORIGINS` to exact frontend HTTPS URL |
| Build fails on poetry/gunicorn | Wrong commands — use pip + uvicorn above |
