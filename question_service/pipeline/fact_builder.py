from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass

from question_service.pipeline.dependency_parser import ParsedFactCore
from question_service.pipeline.ner_extractor import EntityRecord


@dataclass
class Fact:
    fact_id: str
    book_id: str
    chapter: int
    entity: str
    entity_type: str
    lemma: str
    subject: str
    verb: str
    object: str
    sentence: str
    position: int

    def to_dict(self) -> dict:
        return asdict(self)

    def entity_frequency(self, entity_frequency: dict[tuple[str, str], int]) -> int:
        return entity_frequency.get((self.entity, self.entity_type), 0)


class FactBuilder:
    def build(
        self,
        book_id: str,
        chapter: int,
        sentence: str,
        position: int,
        parsed_cores: list[ParsedFactCore],
        entities: list[EntityRecord],
    ) -> list[Fact]:
        facts: list[Fact] = []
        if not entities:
            return facts

        for core in parsed_cores:
            for ent in entities:
                facts.append(
                    Fact(
                        fact_id=str(uuid.uuid4()),
                        book_id=book_id,
                        chapter=chapter,
                        entity=ent.entity,
                        entity_type=ent.entity_type,
                        lemma=core.lemma,
                        subject=core.subject,
                        verb=core.verb,
                        object=core.object,
                        sentence=sentence,
                        position=position,
                    )
                )
        return facts
