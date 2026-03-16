# Deterministic Question Engine

A full-stack demo that generates MCQs from Gutenberg books and serves them by ISBN through a FastAPI backend + React frontend.

## Features

- Offline NLP pipeline: fetch book → chapters → sentence split → NER → dependency parsing → fact extraction/filtering → MCQ + distractors.
- MongoDB persistence for:
  - `books`
  - `book_facts`
  - `entity_bank`
  - `book_questions`
  - `isbn_gutenberg_map` (cached ISBN → Gutenberg mapping + confidence)
- ISBN resolution layer:
  - Fetches title/author from Open Library
  - Searches Gutendex by title
  - Chooses closest match with title/author similarity
  - Caches results to avoid repeated network calls
- API endpoints:
  - `GET /questions/{isbn}` (returns processing/completed/unavailable)
  - `GET /questions/all/{isbn}` (downloads up to 100 questions)
- React demo frontend for portfolio presentation.

## Project Layout

```text
question_service/
  app/
    api/
    controllers/
    services/
    db/
  pipeline/
  scripts/
  config/
frontend/
  src/
    api/
    components/
    pages/
    App.jsx
main.py
requirements.txt
```

## Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Set environment variables:

```bash
export MONGODB_URI="<your_mongodb_atlas_uri>"
export MONGODB_DB="question_service"
export SPACY_MODEL="en_core_web_sm"
# Optional override map: {"9780141439600": {"gutenberg_id": "1342", "title": "Pride and Prejudice", "author": "Jane Austen"}}
export ISBN_SOURCE_MAP='{}'
```

## Run Backend

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `GET /questions/{isbn}`
- `GET /questions/all/{isbn}`

Unavailable response:

```json
{
  "status": "unavailable",
  "message": "This book is not available in the public domain."
}
```


## Quality and Audit Highlights

- ISBN inputs are normalized/validated (10 or 13 digits, hyphens allowed).
- Pipeline stage hardening:
  - improved chapter splitting for `CHAPTER 1`, `CHAPTER I`, and `Chapter One` markers
  - safer SVO extraction + duplicate core elimination
  - fact construction now links entities only when aligned to subject/object mentions
  - distractor generation deduplicates and filters invalid options
- Persistence hardening:
  - entity bank is rebuilt per run (prevents frequency inflation on reprocessing)
  - duplicate question text is deduplicated before insert
- Added unit tests under `tests/` for chapter splitting, fact building/filtering, MCQ generation, distractors, and ISBN normalization.

## Frontend Demo Setup

```bash
cd frontend
npm install
npm run dev
```

Optional frontend env:

```bash
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

Open the app at `http://localhost:5173`.

## Example ISBNs Known to Work with Gutenberg

- `9780141439518` (Pride and Prejudice)
- `9780141439600` (Pride and Prejudice edition)

## Run Offline Pipeline Manually (Optional)

```bash
python -m question_service.scripts.run_pipeline --book_url https://www.gutenberg.org/cache/epub/1342/pg1342.txt --title "Pride and Prejudice" --author "Jane Austen"
```

## Validation Scripts

```bash
python -m question_service.scripts.test_isbn_request --isbn 9780141439600
python -m question_service.scripts.test_questions --book_id 1342
```
