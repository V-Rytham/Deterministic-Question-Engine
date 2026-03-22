"""
Phrase-level SVO + modifiers from spaCy dependency parse (deterministic for fixed model + text).
"""

from server.db.mongo import sentences_col
from server.processing.spacy_model import get_nlp

nlp = get_nlp()


def _subtree_text(token):
    toks = sorted(token.subtree, key=lambda t: t.i)
    return " ".join(t.text for t in toks).strip()


def _find_root(doc):
    for t in doc:
        if t.dep_ == "ROOT":
            return t
    return None


def _child_by_dep(head, deps):
    for c in head.children:
        if c.dep_ in deps:
            return c
    return None


def _collect_prep_phrases(head):
    phrases = []
    for child in head.children:
        if child.dep_ != "prep":
            continue
        pobj = _child_by_dep(child, ("pobj", "pcomp"))
        if pobj is not None:
            phrases.append(f"{child.text} {_subtree_text(pobj)}".strip())
    return phrases


def process_sentence(sent_doc):
    text = sent_doc.get("resolved_text") or sent_doc["text"]
    doc = nlp(text)

    entities = [{"text": e.text, "label": e.label_} for e in doc.ents]

    root = _find_root(doc)
    root_lemma = root.lemma_.lower() if root is not None else None
    root_text = root.text.lower() if root is not None else None

    subject = None
    obj = None
    modifiers = []

    if root is not None:
        for dep in ("nsubj", "nsubjpass", "csubj"):
            c = _child_by_dep(root, (dep,))
            if c is not None:
                subject = _subtree_text(c)
                break

        for dep in ("dobj", "attr", "acomp"):
            c = _child_by_dep(root, (dep,))
            if c is not None and obj is None:
                obj = _subtree_text(c)
                break

        modifiers = _collect_prep_phrases(root)

    return {
        "entities": entities,
        "root": root_text,
        "root_lemma": root_lemma,
        "subject": subject,
        "object": obj,
        "modifiers": modifiers,
        "nlp_text": text,
    }


def run_nlp_pipeline(book_id):
    cursor = sentences_col.find({"book_id": book_id}).sort(
        [("chapter_number", 1), ("para_id", 1), ("order", 1)]
    )

    for sent in cursor:
        result = process_sentence(sent)
        sentences_col.update_one({"_id": sent["_id"]}, {"$set": result})

    # Logging intentionally omitted here; pipeline logs progress.
