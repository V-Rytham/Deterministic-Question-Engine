from __future__ import annotations

from dataclasses import dataclass

from question_service.pipeline.fact_builder import Fact


@dataclass
class QuestionDraft:
    question: str
    answer: str
    answer_type: str
    fact_id: str
    chapter: int


class McqGenerator:
    """Create question drafts from filtered facts using deterministic templates."""

    PERSON_TYPES = {"PERSON"}

    def generate(self, fact: Fact) -> list[QuestionDraft]:
        drafts: list[QuestionDraft] = []
        answer_is_person = fact.entity_type in self.PERSON_TYPES
        wh_word = "Who" if answer_is_person else "What"

        if self._is_same_entity(fact.subject, fact.entity):
            drafts.append(
                QuestionDraft(
                    question=f"{wh_word} {fact.verb} {fact.object}?",
                    answer=fact.subject,
                    answer_type=fact.entity_type,
                    fact_id=fact.fact_id,
                    chapter=fact.chapter,
                )
            )

        drafts.append(
            QuestionDraft(
                question=f"{wh_word} did {fact.subject} {fact.lemma}?",
                answer=fact.object,
                answer_type=fact.entity_type,
                fact_id=fact.fact_id,
                chapter=fact.chapter,
            )
        )

        if fact.entity_type == "EVENT":
            drafts.append(
                QuestionDraft(
                    question=f"During the event, who {fact.verb} {fact.object}?",
                    answer=fact.subject,
                    answer_type="PERSON",
                    fact_id=fact.fact_id,
                    chapter=fact.chapter,
                )
            )

        return [d for d in drafts if self._is_valid_question(d.question)]

    @staticmethod
    def _is_same_entity(left: str, right: str) -> bool:
        return left.strip().lower() == right.strip().lower()

    @staticmethod
    def _is_valid_question(text: str) -> bool:
        cleaned = " ".join(text.split())
        if len(cleaned.split()) < 4:
            return False
        return cleaned.endswith("?")
