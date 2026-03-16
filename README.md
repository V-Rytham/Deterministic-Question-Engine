# Deterministic Question Engine

Standalone Python service that generates MCQs from Gutenberg books using an offline NLP pipeline and serves random precomputed questions through an ISBN-driven API.

## Features

- Offline pipeline: fetch book → chapters → sentence split → NER → dependency parsing → fact extraction/filtering → MCQ + distractors.
- Stores outputs in MongoDB Atlas collections:
  - `books`
  - `book_facts`
  - `entity_bank`
  - `book_questions`
- Runtime API endpoint: `GET /questions/{isbn}`
  - returns 5 random questions instantly when already generated
  - returns processing status and triggers background generation when missing

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

Optional ISBN source mapping (JSON object), used for new ISBN onboarding:

```bash
export ISBN_SOURCE_MAP='{"9780141439600":{"book_url":"https://www.gutenberg.org/cache/epub/1342/pg1342.txt","title":"Pride and Prejudice","author":"Jane Austen"}}'
```

## Run Offline Pipeline

```bash
python -m question_service.scripts.run_pipeline --book_url https://www.gutenberg.org/cache/epub/1342/pg1342.txt --isbn 9780141439600 --title "Pride and Prejudice" --author "Jane Austen"
```

This downloads the book, processes chapters, and stores facts/questions in MongoDB.

## Run API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `GET /questions/{isbn}`

## Validate Generated Questions

By ISBN endpoint:

```bash
python scripts/test_isbn_request.py --isbn 9780141439600
```

Legacy direct DB check by `book_id`:

```bash
python -m question_service.scripts.test_questions --book_id 1342
```

## Render Deployment

- Build command: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add env vars in Render dashboard (`MONGODB_URI`, `MONGODB_DB`, `SPACY_MODEL`, optional `ISBN_SOURCE_MAP`).
