from __future__ import annotations

from dataclasses import dataclass

from question_service.pipeline.nlp import get_nlp


@dataclass
class ParsedFactCore:
    subject: str
    verb: str
    object: str
    lemma: str


class DependencyParser:
    def parse(self, sentence: str) -> list[ParsedFactCore]:
        nlp = get_nlp()
        doc = nlp(sentence)
        facts: list[ParsedFactCore] = []

        for token in doc:
            if token.pos_ != "VERB":
                continue
            subject = self._collect_phrase(token, {"nsubj", "nsubjpass"})
            obj = self._collect_phrase(token, {"dobj", "pobj", "attr", "dative", "obj"})
            if subject and obj:
                facts.append(
                    ParsedFactCore(
                        subject=subject,
                        verb=token.text,
                        object=obj,
                        lemma=token.lemma_,
                    )
                )

        return facts

    @staticmethod
    def _collect_phrase(verb_token, deps: set[str]) -> str:
        for child in verb_token.children:
            if child.dep_ in deps:
                span = child.subtree
                text = " ".join(tok.text for tok in span)
                return text.strip()
        return ""
