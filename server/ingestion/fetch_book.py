import re
import logging
import requests
from requests import RequestException

from server.db.mongo import (
    books_col,
    chapters_col,
    paragraphs_col,
    sentences_col,
    facts_col,
    mcqs_col,
)
from server.utils.errors import BookNotFoundError

logger = logging.getLogger(__name__)


def fetch_book_text(book_id):
    urls = [
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
    ]

    last_err: Exception | None = None

    for url in urls:
        try:
            response = requests.get(url, timeout=60)
        except RequestException as e:
            last_err = e
            continue

        if response.status_code == 200:
            return clean_gutenberg(response.text)

    if last_err is not None:
        raise RuntimeError(f"Network error fetching book id {book_id}") from last_err

    raise BookNotFoundError(f"Book not found for id {book_id}")


def clean_gutenberg(text):
    """Strip Project Gutenberg boilerplate; keep body only."""
    start_markers = ("*** START OF", "***START OF")
    end_markers = ("*** END OF", "***END OF")

    start = -1
    for m in start_markers:
        i = text.find(m)
        if i != -1:
            start = i
            break

    end = -1
    for m in end_markers:
        i = text.find(m)
        if i != -1:
            end = i
            break

    if start != -1 and end != -1 and end > start:
        body = text[start:end]
    elif start != -1:
        body = text[start:]
    elif end != -1:
        body = text[:end]
    else:
        body = text

    # Drop line that is only the START marker
    lines = body.splitlines()
    out = []
    for line in lines:
        if "*** START OF" in line or "***START OF" in line:
            continue
        out.append(line)
    body = "\n".join(out)

    # Normalize whitespace (deterministic)
    body = re.sub(r"\r\n?", "\n", body)
    return body.strip()


def split_into_chapters(text):
    """
    Split on common Gutenberg chapter headings.
    Deterministic: order preserved; first chunk before CHAPTER may be front matter (dropped if short).
    """
    # Split on CHAPTER (Roman or Arabic) or Chapter
    pattern = re.compile(
        r"(?=\n(?:CHAPTER|Chapter)\s+(?:[IVXLCDM]+|\d+|[A-Z][a-z]*)\b)",
        re.MULTILINE,
    )
    parts = pattern.split(text)
    chapters = []
    ch_num = 0
    for part in parts:
        chunk = part.strip()
        if len(chunk) < 500:
            continue
        chapters.append({"chapter_number": ch_num, "text": chunk})
        ch_num += 1

    if not chapters:
        # Fallback: treat whole book as one chapter
        t = text.strip()
        if len(t) >= 500:
            chapters.append({"chapter_number": 0, "text": t})

    return chapters


def clear_book_data(book_id):
    """Remove prior pipeline artifacts for a book (deterministic re-runs)."""
    chapter_ids = [c["_id"] for c in chapters_col.find({"book_id": book_id}, {"_id": 1})]
    para_ids = [
        p["_id"]
        for p in paragraphs_col.find({"chapter_id": {"$in": chapter_ids}}, {"_id": 1})
    ]

    chapters_col.delete_many({"book_id": book_id})
    paragraphs_col.delete_many({"chapter_id": {"$in": chapter_ids}})
    sentences_col.delete_many({"book_id": book_id})
    facts_col.delete_many({"book_id": book_id})
    mcqs_col.delete_many({"book_id": book_id})

    books_col.update_one(
        {"_id": book_id},
        {"$set": {"title": "Unknown Title", "status": "processing"}},
        upsert=True,
    )


def store_book(book_id, title, chapters):
    clear_book_data(book_id)

    books_col.update_one(
        {"_id": book_id},
        {"$set": {"title": title, "status": "processing"}},
        upsert=True,
    )

    for ch in chapters:
        chapters_col.insert_one(
            {
                "book_id": book_id,
                "chapter_number": ch["chapter_number"],
                "text": ch["text"],
            }
        )

    logger.info("Stored %s chapters for book_id=%s", len(chapters), book_id)
