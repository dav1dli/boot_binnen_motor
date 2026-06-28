#!/usr/bin/env python3
"""Generate per-section per-language SSML from a chapter JSON file.

Each section maps to a numbered slide. Output is a batch XML file with one
<segment> per section per language, each containing a standalone <speak>
document ready for Azure Speech TTS.

Audio file naming convention:  chapter-{ch}-{slide:02d}-{lang}.mp3
Example:  chapter-08-01-ru.mp3  (Chapter 8, slide 1, Russian)
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEECH_NS = "http://www.w3.org/2001/10/synthesis"
XML_NS = "http://www.w3.org/XML/1998/namespace"

VOICE_DEFAULTS = {
    "ru": {"voice": "ru-RU-DmitryNeural", "xml_lang": "ru-RU"},
    "de": {"voice": "de-DE-Florian:DragonHDLatestNeural", "xml_lang": "de-DE"},
}


# ---------------------------------------------------------------------------
# Unit abbreviation expansion for TTS
# ---------------------------------------------------------------------------

def expand_units(text: str, lang: str) -> str:
    """Expand measurement abbreviations to full words for TTS pronunciation.

    Handles: m/м (meter), m³/м³/m3/м3 (cubic meters), m²/м²/m2/м2 (square meters),
             km/h/км/ч, kW/кВт, PS/л.с.
    """
    if lang == "de":
        # Order matters: longer patterns first
        text = re.sub(r"(\d)\s*m³", r"\1 Kubikmeter ", text)
        text = re.sub(r"(\d)\s*m3(?!\d)", r"\1 Kubikmeter ", text)
        text = re.sub(r"(\d)\s*m²", r"\1 Quadratmeter ", text)
        text = re.sub(r"(\d)\s*m2(?!\d)", r"\1 Quadratmeter ", text)
        text = re.sub(r"(\d)\s*km/h", r"\1 Kilometer pro Stunde", text)
        text = re.sub(r"(\d)\s*kW", r"\1 Kilowatt", text)
        # "m" as meter — only when preceded by a number and followed by word boundary
        text = re.sub(r"(\d)\s*m\b", r"\1 Meter", text)
    elif lang == "ru":
        text = re.sub(r"(\d)\s*м³", r"\1 кубических метров ", text)
        text = re.sub(r"(\d)\s*м3(?!\d)", r"\1 кубических метров ", text)
        text = re.sub(r"(\d)\s*м²", r"\1 квадратных метров ", text)
        text = re.sub(r"(\d)\s*м2(?!\d)", r"\1 квадратных метров ", text)
        text = re.sub(r"(\d)\s*км/ч", r"\1 километров в час", text)
        text = re.sub(r"(\d)\s*кВт", r"\1 киловатт", text)
        # "м" as meter — only when preceded by a number and followed by word boundary
        text = re.sub(r"(\d)\s*м\b", r"\1 метров", text)
    # Normalize any double spaces introduced by replacements
    text = re.sub(r"  +", " ", text)
    return text


# ---------------------------------------------------------------------------
# Sentence extraction
# ---------------------------------------------------------------------------


def extract_sentences(section: dict, lang: str) -> list[str]:
    """Return all speakable sentences from a section for one language."""
    sentences: list[str] = []

    title = section["title"].get(lang, "")
    if title:
        t = title.strip()
        # Strip (n/m) pagination suffix from split sections
        t = re.sub(r"\s*\(\d+/\d+\)$", "", t)
        if t and t[-1] not in ".!?":
            t += "."
        sentences.append(t)

    for block in section["blocks"]:
        btype = block["type"]
        if btype == "text":
            text = block.get(lang, "")
            if text:
                sentences.append(text.strip())
        elif btype == "key_points":
            for item in block.get("items", []):
                text = item.get(lang, "")
                if text:
                    sentences.append(text.strip())
        elif btype == "key_point":
            text = block.get(lang, "")
            if text:
                sentences.append(text.strip())
        elif btype == "image":
            # Read image caption for TTS
            cap = block.get("caption", {})
            if isinstance(cap, dict):
                text = cap.get(lang, "")
            else:
                text = cap if lang == "de" else ""
            if text:
                sentences.append(text.strip())
        elif btype == "table_row":
            # Table cells are extracted from DE source only; skip for other langs
            if lang == "de":
                cells = block.get("cells", [])
                if cells:
                    row_text = " — ".join(c for c in cells if c)
                    if row_text:
                        sentences.append(row_text.strip())

    # Expand unit abbreviations for TTS
    sentences = [expand_units(s, lang) for s in sentences]

    return sentences


def build_speak(sentences: list[str], lang: str) -> ET.Element:
    """Build a <speak> element for one section in one language."""
    cfg = VOICE_DEFAULTS[lang]
    speak = ET.Element("speak", {
        "version": "1.0",
        "xmlns": SPEECH_NS,
        f"{{{XML_NS}}}lang": cfg["xml_lang"],
    })

    voice = ET.SubElement(speak, "voice", {
        "name": cfg["voice"],
        f"{{{XML_NS}}}lang": cfg["xml_lang"],
    })

    paragraph = ET.SubElement(voice, "p")
    for i, text in enumerate(sentences):
        s_el = ET.SubElement(paragraph, "s")
        s_el.text = text
        if i < len(sentences) - 1:
            ET.SubElement(paragraph, "break", {"time": "600ms"})

    return speak


def build_batch(chapter: dict, languages: list[str]) -> ET.ElementTree:
    """Build a <tts-batch> containing all sections × languages."""
    root = ET.Element("tts-batch")
    ch = chapter["chapter"]

    for slide_num, section in enumerate(chapter["sections"], start=1):
        for lang in languages:
            sentences = extract_sentences(section, lang)
            if not sentences:
                continue

            seg_id = f"chapter-{ch}-{slide_num:02d}-{lang}"
            segment = ET.SubElement(root, "segment", {
                "id": seg_id,
                "chapter": ch,
                "slide": str(slide_num),
                "lang": lang,
                "section-id": section["id"],
            })
            segment.append(build_speak(sentences, lang))

    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    return tree


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate per-section per-language SSML batch from a chapter JSON file."
    )
    parser.add_argument("chapter_file", type=Path, help="Path to chapter-XX.json")
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output SSML batch file (default: same dir, .xml extension)",
    )
    parser.add_argument(
        "--lang", nargs="+", choices=["de", "ru"], default=["de", "ru"],
        help="Languages to generate (default: de ru)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chapter = json.loads(args.chapter_file.read_text(encoding="utf-8"))
    output = args.output or args.chapter_file.with_suffix(".xml")

    tree = build_batch(chapter, args.lang)
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=True)

    count = len(tree.getroot().findall("segment"))
    print(f"Wrote {output} with {count} segments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
