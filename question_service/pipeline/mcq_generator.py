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
    def generate(self, fact: Fact) -> list[QuestionDraft]:
        drafts: list[QuestionDraft] = []
        if fact.subject == fact.entity:
            drafts.append(
                QuestionDraft(
                    question=f"Who {fact.verb} {fact.object}?",
                    answer=fact.subject,
                    answer_type=fact.entity_type,
                    fact_id=fact.fact_id,
                    chapter=fact.chapter,
                )
            )

        drafts.append(
            QuestionDraft(
                question=f"Who did {fact.subject} {fact.lemma}?",
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
                    answer_type=fact.entity_type,
                    fact_id=fact.fact_id,
                    chapter=fact.chapter,
                )
            )

        return [d for d in drafts if len(d.question.split()) > 3]
