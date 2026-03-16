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
    """Extract subject-verb-object tuples from a sentence."""

    def parse(self, sentence: str) -> list[ParsedFactCore]:
        nlp = get_nlp()
        doc = nlp(sentence)
        facts: list[ParsedFactCore] = []

        for token in doc:
            if token.pos_ != "VERB":
                continue
            subject = self._collect_phrase(token, {"nsubj", "nsubjpass"})
            obj = self._collect_object_phrase(token)
            if not subject or not obj:
                continue
            lemma = token.lemma_.strip().lower()
            if not lemma:
                continue
            facts.append(
                ParsedFactCore(
                    subject=subject,
                    verb=token.text.strip(),
                    object=obj,
                    lemma=lemma,
                )
            )

        # dedupe by normalized tuple
        seen: set[tuple[str, str, str, str]] = set()
        unique: list[ParsedFactCore] = []
        for fact in facts:
            key = (
                fact.subject.lower(),
                fact.verb.lower(),
                fact.object.lower(),
                fact.lemma,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(fact)
        return unique

    @staticmethod
    def _collect_phrase(verb_token, deps: set[str]) -> str:
        for child in verb_token.children:
            if child.dep_ in deps:
                return " ".join(tok.text for tok in child.subtree).strip()
        return ""

    @staticmethod
    def _collect_object_phrase(verb_token) -> str:
        direct = {"dobj", "obj", "attr", "dative", "oprd"}
        for child in verb_token.children:
            if child.dep_ in direct:
                return " ".join(tok.text for tok in child.subtree).strip()

        # prepositional object fallback: to/from/of/etc.
        for prep in verb_token.children:
            if prep.dep_ == "prep":
                for pobj in prep.children:
                    if pobj.dep_ == "pobj":
                        return f"{prep.text} {' '.join(tok.text for tok in pobj.subtree)}".strip()
        return ""
