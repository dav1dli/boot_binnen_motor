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
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEECH_NS = "http://www.w3.org/2001/10/synthesis"
XML_NS = "http://www.w3.org/XML/1998/namespace"

VOICE_DEFAULTS = {
    "ru": {"voice": "ru-RU-DmitryNeural", "xml_lang": "ru-RU"},
    "de": {"voice": "de-DE-Florian:DragonHDLatestNeural", "xml_lang": "de-DE"},
}


def extract_sentences(section: dict, lang: str) -> list[str]:
    """Return all speakable sentences from a section for one language."""
    sentences: list[str] = []

    title = section["title"].get(lang, "")
    if title:
        t = title.strip()
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
        # image blocks are skipped

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
