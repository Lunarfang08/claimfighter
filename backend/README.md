# FastAPI Backend Wrapper

REST API wrapper for the Phase 1 medical claim analysis pipeline.

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Running the Server

```bash
# From the backend directory
python api/main.py

# Or with uvicorn directly
uvicorn api.main:app --reload --port 8000
```

Server will be available at: http://localhost:8000

API docs: http://localhost:8000/docs

## API Endpoints

### Health Check
- `GET /` - Health check

### Document Upload
- `POST /api/upload` - Upload a document (PDF/TXT/image)
  - Returns: `case_id`, `filename`, `status`

### Processing
- `POST /api/process/{case_id}` - Trigger pipeline processing
  - Runs: classify → extract → rule engine → risk report

### Appeal Letter Workflow (Phase 2+)
- `GET /api/cases/{case_id}/appeal-letter`
  - Returns: current letter + all stored versions (draft/approved/sent/escalated)
- `POST /api/cases/{case_id}/appeal-letter/approve`
  - Body: `{ version_id, letter_text, notes? }`
  - Creates an immutable `approved` letter version
- `POST /api/cases/{case_id}/appeal-letter/send`
  - Body: `{ version_id, send_method? }`
  - Creates a `sent` letter version and starts the follow-up deadline tracking
- `POST /api/cases/{case_id}/insurer-response`
  - Body: multipart file upload
  - Extracts insurer response and generates a Round 2 `draft` letter version

### Case Management
- `GET /api/cases` - List all cases (optional `?status=` filter)
- `GET /api/cases/{case_id}` - Get case details + risk report
- `GET /api/cases/{case_id}/status` - Get processing status (for polling)
- `DELETE /api/cases/{case_id}` - Delete a case

## Example Usage

```bash
# Upload a document
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@../data/samples/denial_medical_necessity_emergency.txt"

# Response: {"case_id": "123e4567-...", ...}

# Process the case
curl -X POST "http://localhost:8000/api/process/123e4567-..."

# Get the results
curl "http://localhost:8000/api/cases/123e4567-..."
```

## Storage

- `storage/cases.json` - Case metadata and results
- `uploads/` - Uploaded documents

## Configuration

Environment variables (see also [`config.py`](./config.py)):

| Variable | Default | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS origins |
| `STORAGE_DIR` | `backend/storage` | Case JSON directory |
| `UPLOADS_DIR` | `backend/uploads` | Uploaded files directory |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Model name |
| `PORT` | `8000` | Server port (8080 on Fly.io) |

For Fly.io deployment, see [DEPLOY_FLY.md](../DEPLOY_FLY.md) in the repo root.

## Current Limitations
- Storage is file-based JSON (`storage/cases.json`) instead of a production DB
- Background follow-up scheduling is in-process (replace with a durable job queue for real deployments)
- No authentication
- Synchronous processing (async jobs in Phase 4 are not implemented as a durable queue)
