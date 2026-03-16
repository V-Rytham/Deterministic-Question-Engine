from __future__ import annotations

from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from question_service.config.settings import settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(settings.mongodb_uri)


def get_db() -> Database:
    return get_client()[settings.mongodb_db]


def ensure_indexes() -> None:
    db = get_db()
    db.books.create_index("book_id", unique=True)
    db.book_facts.create_index([("book_id", 1), ("chapter", 1), ("position", 1)])
    db.entity_bank.create_index([("book_id", 1), ("entity", 1)], unique=True)
    db.entity_bank.create_index([("book_id", 1), ("entity_type", 1), ("frequency", -1)])
    db.book_questions.create_index([("book_id", 1)])
    db.book_questions.create_index([("book_id", 1), ("question_id", 1)], unique=True)
