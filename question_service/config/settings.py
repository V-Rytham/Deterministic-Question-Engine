from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "question_service")
    spacy_model: str = os.getenv("SPACY_MODEL", "en_core_web_sm")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    # JSON object: {"<isbn>": {"book_url": "...", "title": "...", "author": "..."}}
    isbn_source_map_raw: str = os.getenv("ISBN_SOURCE_MAP", "{}")

    @property
    def isbn_source_map(self) -> dict[str, dict[str, str]]:
        try:
            parsed = json.loads(self.isbn_source_map_raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
        return {}


settings = Settings()
