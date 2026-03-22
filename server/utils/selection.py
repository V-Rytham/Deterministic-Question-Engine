"""
Select top-K MCQs with chapter coverage (round-robin across chapters, then fill by score).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional


def select_top_mcqs(mcqs: List[dict], k: int = 100) -> List[dict]:
    if not mcqs:
        return []

    by_ch: Dict[Optional[int], List[dict]] = defaultdict(list)
    for m in sorted(mcqs, key=lambda x: -float(x.get("quality") or 0.0)):
        ch = m.get("chapter_number")
        by_ch[ch].append(m)

    chapters = sorted(by_ch.keys(), key=lambda c: (c is None, c if c is not None else -1))

    picked: list[dict] = []
    while len(picked) < k:
        progressed = False
        for ch in chapters:
            if len(picked) >= k:
                break
            lst = by_ch[ch]
            if lst:
                picked.append(lst.pop(0))
                progressed = True
        if not progressed:
            break

    if len(picked) < k:
        remainder: list[dict] = []
        for ch in chapters:
            remainder.extend(by_ch[ch])
        remainder.sort(key=lambda x: -float(x.get("quality") or 0.0))
        for m in remainder:
            if len(picked) >= k:
                break
            picked.append(m)

    return picked[:k]

