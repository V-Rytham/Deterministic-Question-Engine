# Deterministic MCQ Generator Engine (FastAPI + MongoDB Atlas)

## Environment variables

- `MONGO_URI` (required): MongoDB Atlas connection string (`mongodb+srv://...`)
- `PORT` (Render provides this automatically)

Optional:
- `MCQ_RETURN_LIMIT` (default `10`)
- `MCQ_TARGET` (default `100`)
- `LOG_LEVEL` (default `INFO`)
- `CORS_ORIGINS` (comma-separated; default `*`)

## Local run

```bash
pip install -r requirements.txt
export MONGO_URI="mongodb+srv://..."
uvicorn main:app --host 0.0.0.0 --port 10000
```

## Render build note (spaCy)

Render must use Python 3.11.x (recommended) or 3.12.x. If Render builds with Python 3.13/3.14, spaCy dependencies (e.g. `blis`, `thinc`) may try to compile and fail.

If you are not using the Blueprint (`render.yaml`), set Render env var:
- `PYTHON_VERSION=3.11.8`

## Endpoints

- `GET /health`
- `POST /generate` with body `{ "book_id": 1342 }`
- `GET /mcqs/{book_id}?limit=10`

## MongoDB

Uses database: `qna_engine`

Collections (auto-created on write):
`books`, `chapters`, `paragraphs`, `sentences`, `facts`, `mcqs`
