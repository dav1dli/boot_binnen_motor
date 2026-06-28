#!/usr/bin/env python3
"""Extract structured chapter JSON from paired DE/RU HTML files.

Reads all sub-page HTML files for a given chapter, extracts content
(headings, paragraphs, images, lists, tables, aside boxes), matches
DE/RU pairs by file number, and produces a structured chapter JSON.

Sections with more than MAX_IMAGES_PER_SECTION images are auto-split
into sub-sections for readable slide generation.

Usage:
    python3 scripts/html_to_chapter_json.py 03
    python3 scripts/html_to_chapter_json.py 03 --max-images 5
    python3 scripts/html_to_chapter_json.py 08 --output data/chapter-08-v2.json
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DE_DIR = ROOT / "content" / "de"
RU_DIR = ROOT / "content" / "ru"

MAX_IMAGES_PER_SECTION = 6
MAX_BLOCKS_PER_SECTION = 15  # total blocks (text + images) before auto-split


# ---------------------------------------------------------------------------
# HTML Content Extractor
# ---------------------------------------------------------------------------

@dataclass
class ContentBlock:
    """A single content block extracted from HTML."""
    type: str  # heading, paragraph, image, list_item, aside, table_row
    text: str = ""
    src: str = ""
    alt: str = ""
    level: int = 0  # for headings: 1, 2, 3
    items: list[str] = field(default_factory=list)  # for tables


class ChapterHTMLParser(HTMLParser):
    """Parse a chapter HTML file and extract ordered content blocks.

    Special handling for <li> elements containing images:
    Images inside a <li> have their adjacent <p> text used as caption,
    rather than emitting a standalone paragraph.
    """

    def __init__(self):
        super().__init__()
        self.blocks: list[ContentBlock] = []
        self._tag_stack: list[str] = []
        self._current_text = ""
        self._in_body = False
        self._in_aside = False
        self._in_table = False
        self._in_li = False
        self._li_images: list[ContentBlock] = []  # images found inside current <li>
        self._current_row: list[str] = []
        self._current_cell = ""
        self._skip_tags = {"style", "script", "head", "title", "meta"}
        self._inline_tags = {"b", "strong", "em", "i", "a", "span", "br", "sup", "sub"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attr_dict = dict(attrs)
        tag_lower = tag.lower()

        if tag_lower == "body":
            self._in_body = True
            return

        if not self._in_body or tag_lower in self._skip_tags:
            return

        self._tag_stack.append(tag_lower)

        if tag_lower in ("h1", "h2", "h3"):
            self._current_text = ""
        elif tag_lower == "p":
            self._current_text = ""
        elif tag_lower == "aside":
            self._in_aside = True
            self._current_text = ""
        elif tag_lower == "img":
            src = attr_dict.get("src", "")
            alt = attr_dict.get("alt", "")
            src = self._normalize_img_src(src)
            if src:
                img = ContentBlock(type="image", src=src, alt=alt)
                if self._in_li:
                    self._li_images.append(img)
                else:
                    self.blocks.append(img)
        elif tag_lower == "table":
            self._in_table = True
        elif tag_lower == "tr":
            self._current_row = []
        elif tag_lower in ("td", "th"):
            self._current_cell = ""
        elif tag_lower == "li":
            self._in_li = True
            self._li_images = []
            self._current_text = ""
        elif tag_lower == "br":
            self._current_text += " "
        elif tag_lower == "figcaption":
            self._current_text = ""

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if not self._in_body:
            return

        if tag_lower in self._skip_tags:
            return

        if self._tag_stack and self._tag_stack[-1] == tag_lower:
            self._tag_stack.pop()

        if tag_lower in ("h1", "h2", "h3"):
            text = self._clean(self._current_text)
            if text:
                level = int(tag_lower[1])
                self.blocks.append(ContentBlock(type="heading", text=text, level=level))
            self._current_text = ""
        elif tag_lower == "p":
            text = self._clean(self._current_text)
            if text and not self._in_table:
                if self._in_li and self._li_images:
                    # This <p> inside a <li> with images: use as caption
                    for img in self._li_images:
                        if not img.alt:
                            img.alt = text
                elif self._in_aside:
                    self.blocks.append(ContentBlock(type="aside", text=text))
                else:
                    self.blocks.append(ContentBlock(type="paragraph", text=text))
            elif text and self._in_table:
                self._current_cell += " " + text
            self._current_text = ""
        elif tag_lower == "aside":
            text = self._clean(self._current_text)
            if text:
                self.blocks.append(ContentBlock(type="aside", text=text))
            self._in_aside = False
            self._current_text = ""
        elif tag_lower == "table":
            self._in_table = False
        elif tag_lower == "tr":
            if self._current_row:
                self.blocks.append(ContentBlock(type="table_row", items=self._current_row[:]))
            self._current_row = []
        elif tag_lower in ("td", "th"):
            self._current_row.append(self._clean(self._current_cell))
            self._current_cell = ""
        elif tag_lower == "li":
            # Finalize <li>: emit images with captions, then leftover text
            if self._li_images:
                # Any remaining text not yet used as caption (plain text after images)
                leftover = self._clean(self._current_text)
                if leftover:
                    for img in self._li_images:
                        if not img.alt:
                            img.alt = leftover
                # Emit all images from this <li>
                self.blocks.extend(self._li_images)
            else:
                # No images in this <li> → emit as list_item
                text = self._clean(self._current_text)
                if text:
                    text = re.sub(r"^[►•·\-–]\s*", "", text)
                    self.blocks.append(ContentBlock(type="list_item", text=text))
            self._in_li = False
            self._li_images = []
            self._current_text = ""
        elif tag_lower == "figcaption":
            text = self._clean(self._current_text)
            if text and self.blocks and self.blocks[-1].type == "image":
                self.blocks[-1].alt = text
            self._current_text = ""

    def handle_data(self, data: str):
        if not self._in_body:
            return
        if self._in_table and ("td" in self._tag_stack or "th" in self._tag_stack):
            self._current_cell += data
        else:
            self._current_text += data

    def _clean(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"^[►•·]\s*", "", text)
        return text

    @staticmethod
    def _normalize_img_src(src: str) -> str:
        """Convert relative paths like ../../images/X.jpg to images/X.jpg"""
        if not src:
            return ""
        src = re.sub(r"^(\.\./)+", "", src)
        return src


def parse_html_file(filepath: Path) -> list[ContentBlock]:
    """Parse an HTML file and return content blocks."""
    parser = ChapterHTMLParser()
    try:
        html_content = filepath.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    parser.feed(html_content)
    blocks = parser.blocks

    # Filter out navigation paragraphs
    NAV_PATTERNS = re.compile(
        r"^(Zurück|Vorwärts|Inhalt|Назад|Вперед|Оглавление|←|→|\s)+$", re.IGNORECASE
    )
    blocks = [b for b in blocks if not (
        b.type == "paragraph" and NAV_PATTERNS.match(b.text)
    )]

    # Post-processing: pair standalone images (no alt) with following paragraph
    merged: list[ContentBlock] = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b.type == "image" and not b.alt:
            # Look ahead for a paragraph to use as caption
            if i + 1 < len(blocks) and blocks[i + 1].type == "paragraph":
                b.alt = blocks[i + 1].text
                merged.append(b)
                i += 2  # skip the paragraph (it's now the caption)
                continue
        merged.append(b)
        i += 1

    return merged


# ---------------------------------------------------------------------------
# Chapter Assembly
# ---------------------------------------------------------------------------

def find_chapter_files(chapter: str) -> list[tuple[Path | None, Path | None]]:
    """Find paired DE/RU files for a chapter, ordered by sub-page number."""
    de_prefix = f"sbf-binnen-de-{chapter}"
    ru_prefix = f"prava-na-lodku-{chapter}"

    # Collect all DE files
    de_files: dict[str, Path] = {}
    for f in sorted(DE_DIR.glob(f"{de_prefix}*.html")):
        # Extract suffix: "" for base, "_1", "_2", etc.
        suffix = f.stem[len(de_prefix):]
        de_files[suffix] = f

    # Collect all RU files
    ru_files: dict[str, Path] = {}
    for f in sorted(RU_DIR.glob(f"{ru_prefix}*.html")):
        suffix = f.stem[len(ru_prefix):]
        ru_files[suffix] = f

    # Merge keys and sort
    all_suffixes = sorted(set(de_files.keys()) | set(ru_files.keys()),
                          key=lambda s: (len(s), s))

    pairs: list[tuple[Path | None, Path | None]] = []
    for suffix in all_suffixes:
        pairs.append((de_files.get(suffix), ru_files.get(suffix)))

    return pairs


@dataclass
class Section:
    """A section ready for JSON output."""
    id: str
    title_de: str
    title_ru: str
    blocks: list[dict[str, Any]]
    terms: list[dict[str, Any]]


def blocks_to_section(
    section_id: str,
    de_blocks: list[ContentBlock],
    ru_blocks: list[ContentBlock],
) -> Section:
    """Convert parsed blocks from DE/RU pair into a Section.

    Preserves document order: text and images are interleaved as they
    appear in the source. Images get bilingual captions from their alt
    text (extracted by the parser from adjacent <p> inside <li>).
    """
    # Extract title from first heading
    title_de = ""
    title_ru = ""
    for b in de_blocks:
        if b.type == "heading":
            title_de = b.text
            break
    for b in ru_blocks:
        if b.type == "heading":
            title_ru = b.text
            break

    # Build a map of RU image alts by src for caption matching
    ru_alt_by_src: dict[str, str] = {}
    for b in ru_blocks:
        if b.type == "image" and b.src and b.alt:
            ru_alt_by_src[b.src] = b.alt

    # Build a map of RU text blocks (paragraphs, list_items, asides) by index
    ru_paragraphs = [b.text for b in ru_blocks if b.type == "paragraph"]
    ru_list_items = [b.text for b in ru_blocks if b.type == "list_item"]
    ru_asides = [b.text for b in ru_blocks if b.type == "aside"]

    json_blocks: list[dict[str, Any]] = []
    para_idx = 0
    list_idx = 0
    aside_idx = 0

    for b in de_blocks:
        if b.type == "heading":
            continue  # Title already extracted

        elif b.type == "paragraph":
            block: dict[str, Any] = {"type": "text", "de": b.text}
            if para_idx < len(ru_paragraphs):
                block["ru"] = ru_paragraphs[para_idx]
            para_idx += 1
            json_blocks.append(block)

        elif b.type == "list_item":
            block = {"type": "text", "de": b.text}
            if list_idx < len(ru_list_items):
                block["ru"] = ru_list_items[list_idx]
            list_idx += 1
            json_blocks.append(block)

        elif b.type == "aside":
            block = {"type": "key_point", "de": b.text}
            if aside_idx < len(ru_asides):
                block["ru"] = ru_asides[aside_idx]
            aside_idx += 1
            json_blocks.append(block)

        elif b.type == "image":
            img_block: dict[str, Any] = {"type": "image", "src": b.src}
            caption: dict[str, str] = {}
            if b.alt:
                caption["de"] = b.alt
            ru_alt = ru_alt_by_src.get(b.src, "")
            if ru_alt:
                caption["ru"] = ru_alt
            if caption:
                img_block["caption"] = caption
            json_blocks.append(img_block)

        elif b.type == "table_row":
            json_blocks.append({"type": "table_row", "cells": b.items})

    # Append any remaining RU-only paragraphs
    while para_idx < len(ru_paragraphs):
        json_blocks.append({"type": "text", "ru": ru_paragraphs[para_idx]})
        para_idx += 1

    return Section(
        id=section_id,
        title_de=title_de,
        title_ru=title_ru,
        blocks=json_blocks,
        terms=[],
    )


def split_section_by_images(section: Section, max_images: int) -> list[Section]:
    """Split a section into sub-sections preserving document order.

    Walks the blocks list in order. When the image count for the current
    chunk reaches max_images, a new sub-section starts. Text blocks that
    appear between images stay with the images they precede/follow.
    """
    images = [b for b in section.blocks if b.get("type") == "image"]
    if len(images) <= max_images:
        return [section]

    # Split blocks into chunks, each with at most max_images images
    chunks: list[list[dict[str, Any]]] = []
    current_chunk: list[dict[str, Any]] = []
    img_count = 0

    for block in section.blocks:
        if block.get("type") == "image":
            if img_count >= max_images:
                # Start new chunk
                chunks.append(current_chunk)
                current_chunk = []
                img_count = 0
            current_chunk.append(block)
            img_count += 1
        else:
            current_chunk.append(block)

    if current_chunk:
        chunks.append(current_chunk)

    # Build sub-sections
    sections: list[Section] = []
    n_chunks = len(chunks)
    for idx, chunk in enumerate(chunks, start=1):
        suffix = chr(ord("a") + idx - 1)
        sub_id = f"{section.id}{suffix}"
        sub_title_de = section.title_de
        sub_title_ru = section.title_ru
        if n_chunks > 1:
            sub_title_de += f" ({idx}/{n_chunks})"
            sub_title_ru += f" ({idx}/{n_chunks})"

        sections.append(Section(
            id=sub_id,
            title_de=sub_title_de,
            title_ru=sub_title_ru,
            blocks=chunk,
            terms=section.terms if idx == 1 else [],
        ))

    return sections


def split_section_by_blocks(section: Section, max_blocks: int) -> list[Section]:
    """Split a section that has too many total blocks (after image split)."""
    if len(section.blocks) <= max_blocks:
        return [section]

    chunks: list[list[dict[str, Any]]] = []
    for i in range(0, len(section.blocks), max_blocks):
        chunks.append(section.blocks[i:i + max_blocks])

    sections: list[Section] = []
    n_chunks = len(chunks)

    # Determine base id (strip existing (x/y) suffix if re-splitting)
    base_id = re.sub(r"[a-z]$", "", section.id)
    # Check if the section already has a letter suffix
    has_suffix = section.id != base_id
    base_title_de = re.sub(r"\s*\(\d+/\d+\)$", "", section.title_de)
    base_title_ru = re.sub(r"\s*\(\d+/\d+\)$", "", section.title_ru)

    for idx, chunk in enumerate(chunks, start=1):
        suffix = chr(ord("a") + idx - 1) if not has_suffix else str(idx)
        sub_id = f"{section.id}-{suffix}" if has_suffix else f"{base_id}{suffix}"
        sub_title_de = base_title_de + f" ({idx}/{n_chunks})" if n_chunks > 1 else base_title_de
        sub_title_ru = base_title_ru + f" ({idx}/{n_chunks})" if n_chunks > 1 else base_title_ru

        sections.append(Section(
            id=sub_id,
            title_de=sub_title_de,
            title_ru=sub_title_ru,
            blocks=chunk,
            terms=section.terms if idx == 1 else [],
        ))

    return sections


def build_chapter_json(
    chapter: str, max_images: int, max_blocks: int,
    page_range: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Build the full chapter JSON structure.

    page_range: optional (start, end) inclusive 0-based page indices.
               Page 0 = base file, 1 = _1, 2 = _2, etc.
    """
    pairs = find_chapter_files(chapter)
    if not pairs:
        raise ValueError(f"No files found for chapter {chapter}")

    # Apply page range filter
    if page_range:
        start, end = page_range
        pairs = pairs[start:end + 1]
        if not pairs:
            raise ValueError(f"No files in page range {start}-{end} for chapter {chapter}")

    all_sections: list[Section] = []
    base_idx = page_range[0] if page_range else 0

    for idx, (de_path, ru_path) in enumerate(pairs):
        de_blocks = parse_html_file(de_path) if de_path else []
        ru_blocks = parse_html_file(ru_path) if ru_path else []

        # Generate section ID (1-based, offset by page range start)
        section_num = base_idx + idx + 1
        section_id = f"{chapter}-{section_num:02d}"

        section = blocks_to_section(section_id, de_blocks, ru_blocks)
        # Split if too many images
        split = split_section_by_images(section, max_images)
        # Second pass: split if too many total blocks
        for s in split:
            all_sections.extend(split_section_by_blocks(s, max_blocks))

    # Extract chapter-level title from first section (strip pagination suffix)
    chapter_title_de = re.sub(r"\s*\(\d+/\d+\)$", "",
                              all_sections[0].title_de if all_sections else f"Chapter {chapter}")
    chapter_title_ru = re.sub(r"\s*\(\d+/\d+\)$", "",
                              all_sections[0].title_ru if all_sections else f"Глава {chapter}")

    # Build output
    output: dict[str, Any] = {
        "chapter": chapter,
        "title": {
            "de": chapter_title_de,
            "ru": chapter_title_ru,
        },
        "source": {
            "de": f"content/de/sbf-binnen-de-{chapter}.html",
            "ru": f"content/ru/prava-na-lodku-{chapter}.html",
        },
        "sections": [],
    }

    for section in all_sections:
        sec_dict: dict[str, Any] = {
            "id": section.id,
            "title": {
                "de": section.title_de,
                "ru": section.title_ru,
            },
            "blocks": section.blocks,
        }
        if section.terms:
            sec_dict["terms"] = section.terms
        output["sections"].append(sec_dict)

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured chapter JSON from paired DE/RU HTML files."
    )
    parser.add_argument("chapter", help="Chapter number, e.g. '03' or '08'")
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output JSON file (default: data/chapter-{ch}.json)",
    )
    parser.add_argument(
        "--max-images", type=int, default=MAX_IMAGES_PER_SECTION,
        help=f"Max images per section before auto-split (default: {MAX_IMAGES_PER_SECTION})",
    )
    parser.add_argument(
        "--max-blocks", type=int, default=MAX_BLOCKS_PER_SECTION,
        help=f"Max total blocks per section before auto-split (default: {MAX_BLOCKS_PER_SECTION})",
    )
    parser.add_argument(
        "--pages", type=str, default=None,
        help="Page range to include, e.g. '0-4' (0=base file, 1=_1, etc.)",
    )
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pretty-print JSON output (default: true)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chapter = args.chapter.zfill(2)
    output = args.output or ROOT / "data" / f"chapter-{chapter}.json"

    # Parse page range
    page_range = None
    if args.pages:
        parts = args.pages.split("-")
        page_range = (int(parts[0]), int(parts[1]))

    try:
        data = build_chapter_json(chapter, args.max_images, args.max_blocks, page_range)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    sections = data["sections"]
    total_images = sum(
        1 for s in sections for b in s["blocks"] if b.get("type") == "image"
    )
    print(f"Wrote {output}")
    print(f"  {len(sections)} sections, {total_images} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
