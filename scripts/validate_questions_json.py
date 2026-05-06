#!/usr/bin/env python3
"""
Validate data/questions.json produced by extract_questions_to_json.py.

Checks:
  * DE and RU question numbering aligns
  * every DE question has 4 answers (Fragenkatalog convention)
  * every DE 'correct' index is in range
  * every RU 'correct' index is in range (or -1 = unknown -> warn only)
  * referenced image files exist on disk

Exit non-zero if any hard error is found.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "questions.json"


def main() -> int:
    if not DATA.exists():
        print(f"ERROR: {DATA} not found - run extract_questions_to_json.py first")
        return 2

    qs = json.loads(DATA.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    seen_ids: set[str] = set()
    by_chapter: dict[str, list[int]] = {}

    for q in qs:
        qid = q["id"]
        if qid in seen_ids:
            errors.append(f"duplicate id {qid}")
        seen_ids.add(qid)

        by_chapter.setdefault(q["chapter"], []).append(q["number"])

        de = q["de"]
        if len(de["answers"]) != 4:
            warnings.append(f"{qid}: DE has {len(de['answers'])} answers (expected 4)")
        if not (0 <= de["correct"] < len(de["answers"])):
            errors.append(f"{qid}: DE correct index out of range")

        ru = q.get("ru")
        if ru is not None:
            if ru["correct"] == -1:
                warnings.append(f"{qid}: RU has no ✓ marker (truncated?)")
            elif not (0 <= ru["correct"] < len(ru["answers"])):
                errors.append(f"{qid}: RU correct index out of range")
            if len(ru["answers"]) != len(de["answers"]):
                warnings.append(
                    f"{qid}: answer-count mismatch DE={len(de['answers'])} RU={len(ru['answers'])}"
                )

        for img in de.get("images", []) + (ru.get("images", []) if ru else []):
            if img.startswith(("http://", "https://", "//")):
                continue  # external image - not validated locally
            if not (ROOT / img).exists():
                errors.append(f"{qid}: missing image {img}")

    # contiguous numbering check (within each chapter, starting from min)
    for chap, nums in by_chapter.items():
        nums_sorted = sorted(nums)
        lo, hi = nums_sorted[0], nums_sorted[-1]
        expected = list(range(lo, hi + 1))
        if nums_sorted != expected:
            missing = sorted(set(expected) - set(nums_sorted))
            extra = sorted(set(nums_sorted) - set(expected))
            errors.append(
                f"chapter {chap}: numbering not contiguous "
                f"(missing={missing[:10]} extra={extra[:10]})"
            )

    print(f"Validated {len(qs)} questions across {len(by_chapter)} chapters.")
    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  FAIL  {e}")

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"\nOK - {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
