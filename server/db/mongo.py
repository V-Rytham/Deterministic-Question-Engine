from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING, MongoClient

from server.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

client = MongoClient(_settings.mongo_uri, serverSelectionTimeoutMS=5000)
db = client[_settings.mongo_db_name]

books_col = db["books"]
chapters_col = db["chapters"]
paragraphs_col = db["paragraphs"]
sentences_col = db["sentences"]
facts_col = db["facts"]
mcqs_col = db["mcqs"]


def init_db() -> None:
    """
    Ensure Mongo connectivity and lightweight indexes.
    MongoDB Atlas auto-creates the DB/collections on first write.
    """
    client.admin.command("ping")

    chapters_col.create_index([("book_id", ASCENDING), ("chapter_number", ASCENDING)])
    paragraphs_col.create_index([("chapter_id", ASCENDING), ("order", ASCENDING)])
    sentences_col.create_index(
        [("book_id", ASCENDING), ("chapter_number", ASCENDING), ("para_id", ASCENDING)]
    )
    facts_col.create_index([("book_id", ASCENDING), ("score", DESCENDING)])
    mcqs_col.create_index([("book_id", ASCENDING), ("quality", DESCENDING)])
