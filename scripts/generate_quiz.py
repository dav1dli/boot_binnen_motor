#!/usr/bin/env python3
"""Generate quiz questions from a chapter JSON file using Azure OpenAI.

Reads a structured chapter JSON, sends the content to Azure OpenAI, and
produces a quiz JSON file with multiple-choice questions.

Required env vars (in env.sh or environment):
    AOAI_ENDPOINT   - Azure OpenAI endpoint URL
    AOAI_KEY        - Azure OpenAI API key
    AOAI_DEPLOYMENT - Model deployment name (e.g. gpt-4o)

Usage:
    python3 scripts/generate_quiz.py data/chapter-08.json
    python3 scripts/generate_quiz.py data/chapter-08.json --lang ru --count 10
    python3 scripts/generate_quiz.py data/chapter-08.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT / "app" / "questions-tts" / "env.sh"

SYSTEM_PROMPT = """\
You are a quiz generator for a boating license learning platform.
Given chapter content in JSON format, generate multiple-choice questions
to test knowledge of the material.

Rules:
- Each question must have exactly 4 answer options
- Exactly one answer must be correct
- Mark the correct answer with its 0-based index
- Questions should cover key concepts, definitions, and practical rules
- Vary difficulty: mix factual recall with applied understanding
- Write questions in the requested language only
- Return ONLY a JSON array, no markdown fences or explanations

Output format (JSON array):
[
  {
    "question": "Question text",
    "answers": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0,
    "section_id": "08-01-hoch-tief",
    "explanation": "Brief explanation why the correct answer is right"
  }
]"""


def parse_env_file(env_file: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_file.exists():
        return values
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_ssl_context(insecure: bool) -> ssl.SSLContext:
    if insecure:
        return ssl._create_unverified_context()
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ModuleNotFoundError:
        return ssl.create_default_context()


def load_aoai_settings(env_file: Path) -> dict[str, str]:
    file_values = parse_env_file(env_file)

    def resolve(name: str) -> str:
        return os.environ.get(name) or file_values.get(name, "")

    endpoint = resolve("AOAI_ENDPOINT").rstrip("/")
    key = resolve("AOAI_KEY")
    deployment = resolve("AOAI_DEPLOYMENT")
    api_version = resolve("AOAI_API_VERSION") or "2024-12-01-preview"

    missing = [
        name
        for name, value in [
            ("AOAI_ENDPOINT", endpoint),
            ("AOAI_KEY", key),
            ("AOAI_DEPLOYMENT", deployment),
        ]
        if not value
    ]
    if missing:
        raise ValueError(
            f"Missing Azure OpenAI configuration: {', '.join(missing)}. "
            f"Set in env.sh or environment variables."
        )

    return {
        "endpoint": endpoint,
        "key": key,
        "deployment": deployment,
        "api_version": api_version,
    }


def build_user_prompt(chapter: dict, lang: str, count: int) -> str:
    """Build the user prompt containing chapter content."""
    lang_label = {"de": "German", "ru": "Russian"}[lang]
    chapter_json = json.dumps(chapter, ensure_ascii=False, indent=2)

    return (
        f"Generate exactly {count} multiple-choice questions in {lang_label} "
        f"based on this chapter content:\n\n{chapter_json}"
    )


def call_aoai(
    settings: dict[str, str],
    system_prompt: str,
    user_prompt: str,
    insecure: bool,
) -> str:
    """Call Azure OpenAI chat completions and return the response text."""
    url = (
        f"{settings['endpoint']}/openai/deployments/{settings['deployment']}"
        f"/chat/completions?api-version={settings['api_version']}"
    )

    payload = json.dumps({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "api-key": settings["key"],
        },
        method="POST",
    )

    ssl_context = build_ssl_context(insecure)

    try:
        with urllib.request.urlopen(request, timeout=120, context=ssl_context) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Azure OpenAI error: HTTP {exc.code} - {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Azure OpenAI error: {exc.reason}") from exc

    content = result["choices"][0]["message"]["content"]

    # Strip markdown code fences if the model wrapped the JSON
    content = content.strip()
    if content.startswith("```"):
        first_newline = content.index("\n")
        content = content[first_newline + 1:]
    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate quiz questions from a chapter JSON using Azure OpenAI."
    )
    parser.add_argument("chapter_file", type=Path, help="Path to chapter-XX.json")
    parser.add_argument(
        "--lang", choices=["de", "ru"], default="de",
        help="Language for generated questions (default: de)",
    )
    parser.add_argument(
        "--count", type=int, default=10,
        help="Number of questions to generate (default: 10)",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output JSON file (default: derived from input)",
    )
    parser.add_argument(
        "--env-file", type=Path, default=DEFAULT_ENV_FILE,
        help=f"Path to env.sh (default: {DEFAULT_ENV_FILE})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the prompt that would be sent without calling Azure OpenAI",
    )
    parser.add_argument(
        "--insecure", action="store_true",
        help="Disable TLS certificate verification",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chapter = json.loads(args.chapter_file.read_text(encoding="utf-8"))
    ch = chapter["chapter"]

    output = args.output or args.chapter_file.parent / f"quiz-{ch}-{args.lang}.json"
    user_prompt = build_user_prompt(chapter, args.lang, args.count)

    if args.dry_run:
        print("=== SYSTEM PROMPT ===")
        print(SYSTEM_PROMPT)
        print("\n=== USER PROMPT ===")
        print(user_prompt[:2000] + "..." if len(user_prompt) > 2000 else user_prompt)
        print(f"\nWould write to: {output}")
        return 0

    aoai_settings = load_aoai_settings(args.env_file)
    response_text = call_aoai(aoai_settings, SYSTEM_PROMPT, user_prompt, args.insecure)

    questions = json.loads(response_text)
    if not isinstance(questions, list):
        raise ValueError(f"Expected a JSON array, got {type(questions).__name__}")

    # Tag each question with chapter
    for q in questions:
        q["chapter"] = ch

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {output} with {len(questions)} questions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
