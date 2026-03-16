from __future__ import annotations

from question_service.pipeline.fact_builder import Fact

PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}
WEAK_VERBS = {
    "be", "is", "was", "were", "am", "are", "been", "being",
    "have", "had", "has", "say", "said", "look", "looked", "go", "went", "come", "came",
}


class FactFilter:
    def filter(self, facts: list[Fact], entity_frequency: dict[tuple[str, str], int]) -> list[Fact]:
        filtered: list[Fact] = []
        for fact in facts:
            if fact.subject.strip().lower() in PRONOUNS:
                continue
            if fact.lemma.strip().lower() in WEAK_VERBS:
                continue
            if fact.entity_frequency(entity_frequency) < 3:
                continue
            if len(fact.sentence.split()) < 6:
                continue
            if not self._contains_entity_mention(fact):
                continue
            filtered.append(fact)
        return filtered

    @staticmethod
    def _contains_entity_mention(fact: Fact) -> bool:
        entity = fact.entity.lower()
        return entity in fact.subject.lower() or entity in fact.object.lower()
