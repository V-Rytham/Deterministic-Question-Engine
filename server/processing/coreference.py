"""
Paragraph-scoped deterministic pronoun resolution using spaCy entities + dependency cues.
No neural coref model: same paragraph + same spaCy model → same output.
"""

from server.db.mongo import chapters_col, paragraphs_col, sentences_col
from server.processing.spacy_model import get_nlp

PRONOUNS = {
    "he",
    "him",
    "his",
    "she",
    "her",
    "hers",
    "they",
    "them",
    "their",
    "theirs",
    "it",
    "its",
}


def _label_compatible(pronoun: str, ent_label: str) -> bool:
    p = pronoun.lower()
    if p in ("he", "him", "his", "she", "her", "hers"):
        return ent_label == "PERSON"
    if p in ("they", "them", "their", "theirs"):
        return ent_label in ("PERSON", "ORG", "GPE", "NORP", "FAC", "EVENT")
    if p in ("it", "its"):
        return ent_label in (
            "ORG",
            "GPE",
            "FAC",
            "EVENT",
            "PRODUCT",
            "WORK_OF_ART",
            "LAW",
            "LANGUAGE",
            "PERSON",
        )
    return False


def _find_antecedent(ents, char_idx: int, pronoun: str):
    before = [e for e in ents if e[1] <= char_idx]
    if not before:
        return None
    compatible = [e for e in before if _label_compatible(pronoun, e[3])]
    if compatible:
        return compatible[-1]
    return before[-1]


def resolve_paragraph_text(para_text: str):
    """Returns list of resolved sentence strings in spaCy sentence order."""
    doc = get_nlp()(para_text)
    ents = [(e.start_char, e.end_char, e.text, e.label_) for e in doc.ents]

    replace_by_tok = {}
    for token in doc:
        if token.lower_ not in PRONOUNS:
            continue
        ante = _find_antecedent(ents, token.idx, token.lower_)
        if ante:
            replace_by_tok[token.i] = ante[2]

    out_sents = []
    for sent in doc.sents:
        buf = []
        for token in sent:
            if token.i in replace_by_tok:
                buf.append(replace_by_tok[token.i])
            else:
                buf.append(token.text)
            buf.append(token.whitespace_)
        out_sents.append("".join(buf).strip())

    return out_sents


def run_coreference_for_book(book_id):
    """Set `resolved_text` on each sentence row (paragraph scope)."""
    ch_query = {"book_id": book_id}
    for ch in chapters_col.find(ch_query).sort("chapter_number", 1):
        for para in paragraphs_col.find({"chapter_id": ch["_id"]}).sort("order", 1):
            para_id = para["_id"]
            sents = list(sentences_col.find({"para_id": para_id}).sort("order", 1))
            if not sents:
                continue

            para_text = para["text"]
            resolved_list = resolve_paragraph_text(para_text)

            if len(resolved_list) != len(sents):
                for s in sents:
                    sentences_col.update_one(
                        {"_id": s["_id"]},
                        {"$set": {"resolved_text": s["text"], "coref_applied": False}},
                    )
                continue

            for sdoc, rtext in zip(sents, resolved_list):
                sentences_col.update_one(
                    {"_id": sdoc["_id"]},
                    {"$set": {"resolved_text": rtext, "coref_applied": True}},
                )

    # Logging intentionally omitted here to keep the core loop tight; pipeline logs progress.
