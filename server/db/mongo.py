from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING, MongoClient

from server.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

MONGO_MISSING_MSG = (
    "MONGO_URI environment variable is required (MongoDB Atlas connection string)."
)


class _UnavailableCollection:
    def __getattr__(self, _name: str):
        raise RuntimeError(MONGO_MISSING_MSG)


client = None
db = None
if _settings.mongo_uri:
    client = MongoClient(_settings.mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[_settings.mongo_db_name]

if db is not None:
    books_col = db["books"]
    chapters_col = db["chapters"]
    paragraphs_col = db["paragraphs"]
    sentences_col = db["sentences"]
    facts_col = db["facts"]
    mcqs_col = db["mcqs"]
else:
    books_col = _UnavailableCollection()
    chapters_col = _UnavailableCollection()
    paragraphs_col = _UnavailableCollection()
    sentences_col = _UnavailableCollection()
    facts_col = _UnavailableCollection()
    mcqs_col = _UnavailableCollection()


def init_db() -> None:
    """
    Ensure Mongo connectivity and lightweight indexes.
    MongoDB Atlas auto-creates the DB/collections on first write.
    """
    if client is None:
        logger.warning("MongoDB is not configured: %s", MONGO_MISSING_MSG)
        return

    client.admin.command("ping")

    chapters_col.create_index([("book_id", ASCENDING), ("chapter_number", ASCENDING)])
    paragraphs_col.create_index([("chapter_id", ASCENDING), ("order", ASCENDING)])
    sentences_col.create_index(
        [("book_id", ASCENDING), ("chapter_number", ASCENDING), ("para_id", ASCENDING)]
    )
    facts_col.create_index([("book_id", ASCENDING), ("score", DESCENDING)])
    mcqs_col.create_index([("book_id", ASCENDING), ("quality", DESCENDING)])
