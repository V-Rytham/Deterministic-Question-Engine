from __future__ import annotations

from functools import lru_cache

import spacy

from question_service.config.settings import settings


@lru_cache(maxsize=1)
def get_nlp():
    try:
        return spacy.load(settings.spacy_model)
    except OSError:
        return spacy.load("en_core_web_sm")
