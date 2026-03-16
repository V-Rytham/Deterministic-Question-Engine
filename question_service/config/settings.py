from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _parse_isbn_source_map() -> dict[str, dict]:
    raw = os.getenv("ISBN_SOURCE_MAP", "")
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "question_service")
    spacy_model: str = os.getenv("SPACY_MODEL", "en_core_web_sm")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    isbn_source_map: dict[str, dict] = field(default_factory=_parse_isbn_source_map)


settings = Settings()
