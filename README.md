# Deterministic Question Engine

Standalone Python service that generates MCQs from Gutenberg books using an offline NLP pipeline and serves random precomputed questions instantly via API.

## Features

- Offline pipeline: fetch book → chapters → sentence split → NER → dependency parsing → fact extraction/filtering → MCQ + distractors.
- Stores outputs in MongoDB Atlas collections:
  - `books`
  - `book_facts`
  - `entity_bank`
  - `book_questions`
- Runtime API endpoint: `GET /questions/{book_id}` returns 5 random MCQs.

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
main.py
requirements.txt
```

## Setup

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
```

## Run Offline Pipeline

```bash
python -m question_service.scripts.run_pipeline --book_url https://www.gutenberg.org/cache/epub/1342/pg1342.txt --title "Pride and Prejudice" --author "Jane Austen"
```

This downloads the book, processes chapters, and stores facts/questions in MongoDB.

## Run API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `GET /questions/{book_id}`

## Validate Generated Questions

```bash
python -m question_service.scripts.test_questions --book_id 1342
```

## Render Deployment

- Build command: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add env vars in Render dashboard (`MONGODB_URI`, `MONGODB_DB`, `SPACY_MODEL`).
