from __future__ import annotations

import os
from dataclasses import dataclass

try:
    # Optional local development convenience; `.env` is gitignored.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _get_env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v or None


def _parse_int(name: str, default: int) -> int:
    raw = _get_env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise RuntimeError(f"Invalid {name}: expected int, got {raw!r}") from e


def _parse_csv(name: str) -> list[str] | None:
    raw = _get_env(name)
    if raw is None:
        return None
    parts = [p.strip() for p in raw.split(",")]
    parts = [p for p in parts if p]
    return parts or None


@dataclass(frozen=True)
class Settings:
    mongo_uri: str | None = None
    mongo_db_name: str = "qna_engine"
    mcq_return_limit: int = 10
    mcq_target: int = 100
    pipeline_lock_ttl_seconds: int = 60 * 60  # 1 hour
    pipeline_workers: int = 4
    spacy_batch_size: int = 32
    cors_origins: list[str] | None = None
    log_level: str = "INFO"


def get_settings() -> Settings:
    mongo_uri = _get_env("MONGO_URI")
    cors_origins = _parse_csv("CORS_ORIGINS")

    return Settings(
        mongo_uri=mongo_uri,
        mongo_db_name=_get_env("MONGO_DB_NAME") or "qna_engine",
        mcq_return_limit=_parse_int("MCQ_RETURN_LIMIT", 10),
        mcq_target=_parse_int("MCQ_TARGET", 100),
        pipeline_lock_ttl_seconds=_parse_int("PIPELINE_LOCK_TTL_SECONDS", 60 * 60),
        pipeline_workers=_parse_int("PIPELINE_WORKERS", 4),
        spacy_batch_size=_parse_int("SPACY_BATCH_SIZE", 32),
        cors_origins=cors_origins,
        log_level=_get_env("LOG_LEVEL") or "INFO",
    )
