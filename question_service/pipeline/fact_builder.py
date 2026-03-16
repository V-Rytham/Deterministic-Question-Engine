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
    """Build candidate facts by linking parsed SVO cores to entity mentions."""

    def build(
        self,
        book_id: str,
        chapter: int,
        sentence: str,
        position: int,
        parsed_cores: list[ParsedFactCore],
        entities: list[EntityRecord],
    ) -> list[Fact]:
        if not entities or not parsed_cores:
            return []

        sentence_l = sentence.lower()
        entity_pairs = {(e.entity.strip(), e.entity_type) for e in entities if e.entity.strip()}
        facts: list[Fact] = []
        seen: set[tuple[str, str, str, str, int]] = set()

        for core in parsed_cores:
            for entity, entity_type in entity_pairs:
                entity_l = entity.lower()
                # Keep only meaningful alignments.
                if entity_l not in sentence_l:
                    continue
                if entity_l not in core.subject.lower() and entity_l not in core.object.lower():
                    continue

                key = (core.subject.lower(), core.lemma.lower(), core.object.lower(), entity_l, position)
                if key in seen:
                    continue
                seen.add(key)
                facts.append(
                    Fact(
                        fact_id=str(uuid.uuid4()),
                        book_id=book_id,
                        chapter=chapter,
                        entity=entity,
                        entity_type=entity_type,
                        lemma=core.lemma,
                        subject=core.subject,
                        verb=core.verb,
                        object=core.object,
                        sentence=sentence,
                        position=position,
                    )
                )

        return facts
