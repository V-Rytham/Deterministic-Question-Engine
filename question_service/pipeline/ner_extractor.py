from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from question_service.pipeline.nlp import get_nlp

ALLOWED_ENTITY_TYPES = {"PERSON", "ORG", "GPE", "LOC", "EVENT"}


@dataclass
class EntityRecord:
    entity: str
    entity_type: str
    sentence: str


class NerExtractor:
    def extract(self, sentence: str) -> list[EntityRecord]:
        nlp = get_nlp()
        doc = nlp(sentence)
        entities: list[EntityRecord] = []
        for ent in doc.ents:
            if ent.label_ in ALLOWED_ENTITY_TYPES:
                entities.append(EntityRecord(entity=ent.text.strip(), entity_type=ent.label_, sentence=sentence))
        return entities

    @staticmethod
    def frequency_map(entities: list[EntityRecord]) -> Counter:
        return Counter((item.entity, item.entity_type) for item in entities)
