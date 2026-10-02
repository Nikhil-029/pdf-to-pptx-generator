# PDF → PPTX Generator API

Turn a raw PDF report into a client-ready slide deck in minutes. Upload a
PDF, and a two-stage LLM pipeline (content planning → outline generation)
extracts the key points and renders them into a designed PowerPoint file —
no manual copy-pasting from a report into slides.

Converts a PDF document into a professional PowerPoint presentation using a
**true microservice architecture**: a FastAPI API server, a Celery worker, Redis,
and MinIO all run as separate Docker services.

---

## Architecture

```
┌─────────────┐    POST /generate-async     ┌────────────────────┐
│   Frontend  │ ─────────────────────────► │   FastAPI (API)    │
│             │ ◄─────────────────────────  │   :8000            │
│             │    {job_id, poll_url}       └────────┬───────────┘
│             │                                      │ enqueues task
│             │    GET /jobs/{job_id}                ▼
│             │ ──────────────────────►  ┌─────────────────────┐
│             │ ◄──────────────────────  │   Redis             │
│             │   {status, progress%}    │   :6379             │
│             │                          └──────────┬──────────┘
│             │    GET /download/{file}              │ task picked up
│             │ ──────────────────────►             ▼
└─────────────┘                         ┌─────────────────────┐
                                        │   Celery Worker     │
                                        │                     │
                                        │  1. Extract text    │
                                        │  2. LLM outline     │
                                        │  3. Fetch images    │
                                        │  4. Render PPTX     │
                                        └──────────┬──────────┘
                                                   │ saves .pptx
                                                   ▼
                                        ┌─────────────────────┐
                                        │   outputs/          │
                                        │   (local or MinIO)  │
                                        └─────────────────────┘
```

## Job Status Flow

```
queued → extracting (10%) → generating_outline (30%)
       → fetching_images (60%) → rendering_pptx (80%) → completed (100%)
                                                       → failed
```

---

## Quick Start

### 1. Copy environment variables
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Start all services with Docker
```bash
docker-compose up --build
```

| Service     | URL                          | Description              |
|-------------|------------------------------|--------------------------|
| API docs    | http://localhost:8000/docs   | Swagger UI               |
| Flower      | http://localhost:5555        | Celery task monitor      |
| MinIO UI    | http://localhost:9001        | Object storage browser   |

### 3. Without Docker (development)
```bash
pip install -r requirements.txt

# Terminal 1 – API server
uvicorn app.main:app --reload

# Terminal 2 – Celery worker (requires Redis running)
celery -A app.worker worker --loglevel=info
```

### 4. Demo UI (optional)

A simple Streamlit frontend (`app/ui.py`) wraps the API with a file upload,
a live progress bar tied to the job's actual pipeline stage, and a download
button — useful for demos without needing `curl`/Postman.

```bash
streamlit run app/ui.py
```

Requires the API server (step 2 or 3) already running on `localhost:8000`.

---

## API Reference

### `POST /api/v1/pdf/generate-async`
Upload a PDF and start processing. Returns immediately with a `job_id`.

```bash
curl -X POST http://localhost:8000/api/v1/pdf/generate-async \
  -F "file=@your_document.pdf"
```

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "queued",
  "poll_url": "/api/v1/pdf/jobs/abc-123"
}
```

### `GET /api/v1/pdf/jobs/{job_id}`
Poll for progress. The `progress` field goes from 0 → 100.

```json
{
  "job_id": "abc-123",
  "status": "generating_outline",
  "progress": 30,
  "result": null,
  "error": null
}
```

When `status == "completed"`:
```json
{
  "status": "completed",
  "progress": 100,
  "result": {
    "document_title": "...",
    "slide_count": 8,
    "download_url": "/api/v1/pdf/download/abc-123_presentation.pptx"
  }
}
```

### `GET /api/v1/pdf/download/{filename}`
Download the generated `.pptx` file.

---

## Key Improvements over v1

| Issue (v1)                           | Fix (v2)                                             |
|--------------------------------------|------------------------------------------------------|
| All logic in one commented-out file  | Clean separation: routes → orchestrator → services   |
| No progress feedback during LLM wait | Granular progress (10/30/60/80/100%) via Redis       |
| `JOB_TRACKER` dict lost on restart   | `JobStore` backed by Redis (with in-memory fallback) |
| Config constants scattered           | `pydantic-settings` with `.env` file support         |
| No error surface to client           | Every step caught; `error` field in job status       |
| API server blocks during processing  | FastAPI `BackgroundTasks` + Celery worker option      |
| Hardcoded API keys in source         | All secrets via environment variables                 |
| No path-traversal protection         | Download endpoint sanitises filename                  |
| No structured logging                | Timestamps + log levels on every operation            |

---

## Demo tips

- Use a text-heavy PDF (a report, whitepaper, or article) rather than a
  scanned image-only PDF — text extraction is what feeds the outline stage
- Watch the `progress` field move through each stage via
  `GET /jobs/{job_id}` — that visible pipeline (extract → outline → images
  → render) is what makes this feel like a real system rather than a single
  black-box API call
- The `UNSPLASH_ACCESS_KEY` is optional — without it, slides render without
  stock background images but the pipeline still completes end to end

