#!/usr/bin/env python3
"""
Extract Sportbootfuehrerschein Binnen Fragenkatalog from the bilingual HTML
files into a single AI-friendly JSON document.

Inputs (paired by chapter):
    content/de/sbf-binnen-de-11.html      <-> content/ru/prava-na-lodku-11.html      (Basisfragen,    72 Q)
    content/de/sbf-binnen-de-11_1.html    <-> content/ru/prava-na-lodku-11_1.html    (Spezifisch,    181 Q)

Output:
    data/questions.json   - list of merged question objects

DE convention: answers live in <ol type="a"><li>...</li></ol>; the first
answer (a) is always the correct one (per the file's own annotation).
RU convention: answers live inside a two-column <table>; the answer prefixed
with U+2713 (CHECK MARK) is correct, others use U+25A1 (WHITE SQUARE).

Usage:
    python3 scripts/extract_questions_to_json.py
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    sys.stderr.write(
        "ERROR: BeautifulSoup4 is required.  Install with:\n"
        "    python3 -m pip install beautifulsoup4\n"
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
DE_DIR = ROOT / "content" / "de"
RU_DIR = ROOT / "content" / "ru"
OUT = ROOT / "data" / "questions.json"

PAIRS = [
    # (chapter_id, de_file, ru_file, category)
    ("11",   "sbf-binnen-de-11.html",   "prava-na-lodku-11.html",   "basis"),
    ("11_1", "sbf-binnen-de-11_1.html", "prava-na-lodku-11_1.html", "spezifisch"),
    ("11_2", "sbf-binnen-de-11_2.html", "prava-na-lodku-11_2.html", "segeln"),
]

CHECK = "\u2713"   # ✓
SQUARE = "\u25a1"  # □

QNUM_RE = re.compile(r"^\s*(\d+)\.\s*(.*)", re.S)


@dataclass
class Lang:
    question: str
    answers: list[str]
    correct: int            # 0-based index into answers
    images: list[str] = field(default_factory=list)
    source_anchor: str = ""


@dataclass
class Question:
    id: str
    chapter: str
    category: str
    number: int
    de: Lang
    ru: Lang | None = None


# ---------------------------------------------------------------------------
# DE extraction
# ---------------------------------------------------------------------------

def _collect_images_until(node: Tag, stop) -> list[str]:
    """Collect <img src> from following siblings until `stop` predicate."""
    imgs: list[str] = []
    for sib in node.next_siblings:
        if isinstance(sib, Tag):
            if stop(sib):
                break
            for img in sib.find_all("img"):
                src = img.get("src", "")
                if src:
                    imgs.append(_normalise_src(src))
    return imgs


def _normalise_src(src: str) -> str:
    # Strip "../../" prefix so paths are workspace-relative.
    return re.sub(r"^(\.\./)+", "", src)


def extract_de(html_path: Path) -> dict[int, Lang]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    body = soup.body or soup
    out: dict[int, Lang] = {}

    paragraphs = body.find_all("p")
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        m = QNUM_RE.match(text)
        if not m:
            continue
        # ensure the next non-text sibling is an <ol>
        ol = p.find_next_sibling()
        # skip whitespace text nodes
        while ol is not None and isinstance(ol, NavigableString):
            ol = ol.next_sibling
        if not (isinstance(ol, Tag) and ol.name == "ol"):
            continue

        qnum = int(m.group(1))
        question = m.group(2).strip()
        # Strip surrounding whitespace/newlines from question
        question = re.sub(r"\s+", " ", question)

        answers = [
            re.sub(r"\s+", " ", li.get_text(" ", strip=True)).strip()
            for li in ol.find_all("li", recursive=False)
        ]
        # Per file convention: answer (a) is always correct.
        correct = 0

        # images: any <img> inside the question <p>, the <ol>, or sibling
        # <p>/<img> blocks until the next numbered question.
        imgs: list[str] = []
        for img in p.find_all("img"):
            imgs.append(_normalise_src(img.get("src", "")))
        for img in ol.find_all("img"):
            imgs.append(_normalise_src(img.get("src", "")))
        # Look at siblings between <ol> and the next numbered <p>
        for sib in ol.next_siblings:
            if isinstance(sib, Tag):
                if sib.name == "p":
                    txt = sib.get_text(" ", strip=True)
                    if QNUM_RE.match(txt):
                        break
                if sib.name == "ol":
                    # next question's <ol> reached without a leading <p>?
                    break
                for img in sib.find_all("img") if hasattr(sib, "find_all") else []:
                    imgs.append(_normalise_src(img.get("src", "")))

        out[qnum] = Lang(
            question=question,
            answers=answers,
            correct=correct,
            images=[i for i in imgs if i],
            source_anchor=f"q{qnum}",
        )
    return out


# ---------------------------------------------------------------------------
# RU extraction
# ---------------------------------------------------------------------------

_MARKER_RE = re.compile(rf"[{CHECK}{SQUARE}]\s*")


def _split_ru_answers(cell_text: str) -> tuple[list[str], int]:
    """
    Given the textual content of an answer <td>, split on ✓/□ markers and
    return (answers, correct_index).  Falls back gracefully if markers are
    absent or malformed.
    """
    # Normalise whitespace
    text = re.sub(r"\s+", " ", cell_text).strip()
    # Find every marker position
    parts: list[tuple[str, int]] = []  # (answer_text, is_correct)
    i = 0
    while i < len(text):
        c = text[i]
        if c in (CHECK, SQUARE):
            is_correct = c == CHECK
            j = i + 1
            # advance until next marker
            while j < len(text) and text[j] not in (CHECK, SQUARE):
                j += 1
            ans = text[i + 1 : j].strip(" .;:\u00a0")
            ans = ans.strip()
            parts.append((ans, 1 if is_correct else 0))
            i = j
        else:
            i += 1
    if not parts:
        # No markers -> treat entire cell as one answer with unknown correct
        return ([text], -1)

    answers = [a for a, _ in parts]
    correct_idx = next((idx for idx, (_, c) in enumerate(parts) if c), -1)
    return (answers, correct_idx)


def extract_ru(html_path: Path) -> dict[int, Lang]:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    out: dict[int, Lang] = {}

    # Try table-based extraction first (the original RU format).
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 2:
            continue
        q_text = tds[0].get_text(" ", strip=True)
        m = QNUM_RE.match(q_text)
        if not m:
            continue
        qnum = int(m.group(1))
        question = re.sub(r"\s+", " ", m.group(2)).strip()

        answer_cell_text = tds[1].get_text(" ", strip=True)
        answers, correct = _split_ru_answers(answer_cell_text)

        imgs = [
            _normalise_src(img.get("src", ""))
            for td in tds
            for img in td.find_all("img")
        ]

        out[qnum] = Lang(
            question=question,
            answers=answers,
            correct=correct,
            images=[i for i in imgs if i],
            source_anchor=f"q{qnum}",
        )

    # If no table rows found, fall back to <ol>-list format (same as DE).
    if not out:
        out = extract_de(html_path)

    return out


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge(chapter: str, category: str, de: dict[int, Lang], ru: dict[int, Lang]) -> list[Question]:
    qs: list[Question] = []
    for n in sorted(set(de) | set(ru)):
        de_q = de.get(n)
        ru_q = ru.get(n)
        if de_q is None:
            # Skip questions only present in RU (DE is the master source).
            continue
        qid = f"q-{category[:4]}-{chapter}-{n:03d}"
        qs.append(Question(
            id=qid,
            chapter=chapter,
            category=category,
            number=n,
            de=de_q,
            ru=ru_q,
        ))
    return qs


def to_jsonable(qs: Iterable[Question]) -> list[dict]:
    out = []
    for q in qs:
        d = asdict(q)
        if d["ru"] is None:
            d.pop("ru")
        out.append(d)
    return out


def main() -> int:
    all_qs: list[Question] = []
    for chapter, de_name, ru_name, category in PAIRS:
        de_path = DE_DIR / de_name
        ru_path = RU_DIR / ru_name
        if not de_path.exists():
            print(f"WARN: missing {de_path}", file=sys.stderr)
            continue
        de = extract_de(de_path)
        ru = extract_ru(ru_path) if ru_path.exists() else {}
        merged = merge(chapter, category, de, ru)
        print(f"{chapter}: DE={len(de)}  RU={len(ru)}  merged={len(merged)}")
        all_qs.extend(merged)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(to_jsonable(all_qs), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {len(all_qs)} questions to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
