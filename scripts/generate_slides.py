#!/usr/bin/env python3
"""Generate a reveal.js slide deck from a chapter JSON file.

Produces a self-contained HTML file using reveal.js from CDN.
Each section becomes a numbered slide.  Audio references follow the
naming convention chapter-{ch}-{slide:02d}-{lang}.mp3.

Usage:
    python3 scripts/generate_slides.py data/chapter-08.json --lang de
    python3 scripts/generate_slides.py data/chapter-08.json --lang ru -o slides-08-ru.html
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVEAL_CSS = "https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css"
REVEAL_THEME = "https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/white.css"
REVEAL_JS = "https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.esm.js"


def e(text: str) -> str:
    """HTML-escape text."""
    return html.escape(text, quote=True)


def slide_html(
    chapter: dict,
    section: dict,
    slide_num: int,
    lang: str,
    audio_dir: str,
) -> str:
    """Render one <section> slide for a reveal.js deck."""
    ch = chapter["chapter"]
    title = section["title"].get(lang, "")
    audio_file = f"{audio_dir}/chapter-{ch}-{slide_num:02d}-{lang}.mp3"

    lines: list[str] = []
    lines.append("      <section>")
    lines.append(f"        <h2>{e(title)}</h2>")

    # Collect key_points for bullet list
    bullets: list[str] = []
    # Collect text blocks for speaker notes
    notes: list[str] = []
    # Collect images
    images: list[dict] = []

    for block in section["blocks"]:
        btype = block["type"]
        if btype == "key_points":
            for item in block.get("items", []):
                text = item.get(lang, "")
                if text:
                    bullets.append(text)
        elif btype == "text":
            text = block.get(lang, "")
            if text:
                notes.append(text)
        elif btype == "image":
            if block.get("role") == "chapter-header":
                continue
            images.append(block)

    # Images
    for img in images:
        src = img.get("src", "")
        caption = ""
        cap_obj = img.get("caption")
        if isinstance(cap_obj, dict):
            caption = cap_obj.get(lang, "")
        elif isinstance(cap_obj, str):
            caption = cap_obj
        lines.append(f'        <img src="{e(src)}" alt="{e(caption)}"')
        lines.append(f'             style="max-height: 300px; margin: 0.5em auto;">')

    # Bullet list
    if bullets:
        lines.append("        <ul>")
        for b in bullets:
            lines.append(f"          <li>{e(b)}</li>")
        lines.append("        </ul>")
    elif not images:
        # If no key_points and no images, show first text block on slide
        if notes:
            lines.append(f"        <p style=\"font-size:0.7em; text-align:left;\">{e(notes[0])}</p>")

    # Audio player
    lines.append(f'        <audio data-autoplay data-src="{e(audio_file)}"></audio>')

    # Speaker notes (all text blocks)
    if notes:
        lines.append("        <aside class=\"notes\">")
        for n in notes:
            lines.append(f"          <p>{e(n)}</p>")
        lines.append("        </aside>")

    lines.append("      </section>")
    return "\n".join(lines)


def build_html(chapter: dict, lang: str, audio_dir: str) -> str:
    """Build the full reveal.js HTML document."""
    ch = chapter["chapter"]
    chapter_title = chapter["title"].get(lang, f"Chapter {ch}")
    other_lang = "ru" if lang == "de" else "de"
    subtitle = chapter["title"].get(other_lang, "")

    # Title slide
    title_slide = f"""      <section>
        <h1>{e(chapter_title)}</h1>
        <p style="opacity:0.6">{e(subtitle)}</p>
        <p style="font-size:0.6em; opacity:0.4">Chapter {ch}</p>
      </section>"""

    # Content slides
    content_slides: list[str] = []
    for slide_num, section in enumerate(chapter["sections"], start=1):
        content_slides.append(
            slide_html(chapter, section, slide_num, lang, audio_dir)
        )

    # Terms slide (glossary)
    all_terms: list[dict] = []
    for section in chapter["sections"]:
        all_terms.extend(section.get("terms", []))

    terms_slide_lines = ["      <section>", "        <h2>Glossar / Глоссарий</h2>"]
    if all_terms:
        terms_slide_lines.append('        <table style="font-size:0.55em; width:90%; margin:auto;">')
        terms_slide_lines.append("          <tr><th>Deutsch</th><th>Русский</th></tr>")
        for term in all_terms:
            de_term = term.get("de", "")
            ru_term = term.get("ru", "")
            terms_slide_lines.append(
                f"          <tr><td>{e(de_term)}</td><td>{e(ru_term)}</td></tr>"
            )
        terms_slide_lines.append("        </table>")
    terms_slide_lines.append("      </section>")
    terms_slide = "\n".join(terms_slide_lines)

    slides_joined = "\n".join(content_slides)

    return f"""<!DOCTYPE html>
<html lang="{e(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(chapter_title)} — Chapter {ch}</title>
  <link rel="stylesheet" href="{REVEAL_CSS}">
  <link rel="stylesheet" href="{REVEAL_THEME}">
  <style>
    .reveal h1, .reveal h2 {{ text-transform: none; }}
    .reveal ul {{ text-align: left; font-size: 0.75em; }}
    .reveal table {{ border-collapse: collapse; }}
    .reveal td, .reveal th {{ border: 1px solid #ccc; padding: 0.3em 0.6em; }}
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
{title_slide}
{slides_joined}
{terms_slide}
    </div>
  </div>
  <script type="module">
    import Reveal from '{REVEAL_JS}';
    Reveal.initialize({{
      hash: true,
      slideNumber: true,
    }});
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a reveal.js slide deck from a chapter JSON file."
    )
    parser.add_argument("chapter_file", type=Path, help="Path to chapter-XX.json")
    parser.add_argument(
        "--lang", choices=["de", "ru"], default="de",
        help="Presentation language (default: de)",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output HTML file (default: derived from input)",
    )
    parser.add_argument(
        "--audio-dir", default="audio/chapters",
        help="Relative path to audio files from the HTML file (default: audio/chapters)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chapter = json.loads(args.chapter_file.read_text(encoding="utf-8"))
    ch = chapter["chapter"]

    output = args.output or args.chapter_file.parent / f"slides-{ch}-{args.lang}.html"
    html_content = build_html(chapter, args.lang, args.audio_dir)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_content, encoding="utf-8")

    slide_count = len(chapter["sections"]) + 2  # title + content + glossary
    print(f"Wrote {output} ({slide_count} slides, lang={args.lang})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
