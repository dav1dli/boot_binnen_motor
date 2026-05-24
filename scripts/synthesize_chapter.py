#!/usr/bin/env python3
"""Synthesize chapter SSML batch to per-section per-language MP3 files.

Reads a batch XML produced by generate_chapter_ssml.py.  Each <segment>
becomes one Azure Speech REST call and one MP3 file named after the
segment id, e.g. chapter-08-01-ru.mp3.

Uses the same env.sh configuration as synthesize_questions.py.
"""
from __future__ import annotations

import argparse
import os
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT / "app" / "questions-tts" / "env.sh"
DEFAULT_OUTPUT_DIR = ROOT / "audio" / "chapters"


@dataclass(frozen=True)
class Settings:
    speech_key: str
    speech_region: str
    output_format: str
    insecure_ssl: bool


def build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ModuleNotFoundError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


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


def load_settings(env_file: Path, insecure: bool) -> Settings:
    file_values = parse_env_file(env_file)

    def resolve(name: str) -> str:
        return os.environ.get(name) or file_values.get(name, "")

    speech_key = resolve("SPEECH_KEY")
    speech_region = resolve("SPEECH_REGION")
    if not speech_key:
        raise ValueError("SPEECH_KEY is required (set in env.sh or environment)")
    if not speech_region:
        raise ValueError("SPEECH_REGION is required (set in env.sh or environment)")

    return Settings(
        speech_key=speech_key,
        speech_region=speech_region,
        output_format=resolve("TTS_OUTPUT_FORMAT") or "audio-24khz-96kbitrate-mono-mp3",
        insecure_ssl=insecure or resolve("TTS_INSECURE_SSL").lower() in {"1", "true", "yes", "on"},
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def synthesize_segments(
    batch_file: Path,
    output_dir: Path,
    settings: Settings,
    dry_run: bool,
) -> int:
    tree = ET.parse(batch_file)
    root = tree.getroot()
    if root.tag != "tts-batch":
        raise ValueError("Root element must be <tts-batch>")

    segments = root.findall("segment")
    if not segments:
        raise ValueError("No <segment> elements found in the batch file")

    endpoint = (
        f"https://{settings.speech_region}.tts.speech.microsoft.com"
        f"/cognitiveservices/v1"
    )
    ssl_context = (
        ssl._create_unverified_context()
        if settings.insecure_ssl
        else build_ssl_context()
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    for segment in segments:
        seg_id = segment.attrib.get("id", "unknown")
        destination = output_dir / f"{seg_id}.mp3"

        speak = next(
            (child for child in segment if local_name(child.tag) == "speak"),
            None,
        )
        if speak is None:
            raise ValueError(f"Segment {seg_id} has no <speak> element")

        ssml = ET.tostring(speak, encoding="unicode")

        if dry_run:
            print(f"DRY RUN {seg_id} -> {destination}")
            continue

        request = urllib.request.Request(
            endpoint,
            data=ssml.encode("utf-8"),
            headers={
                "Content-Type": "application/ssml+xml",
                "Ocp-Apim-Subscription-Key": settings.speech_key,
                "X-Microsoft-OutputFormat": settings.output_format,
                "User-Agent": "boot-binnen-motor-tts",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120, context=ssl_context) as response:
                destination.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Synthesis failed for {seg_id}: HTTP {exc.code} - {details}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Synthesis failed for {seg_id}: {exc.reason}"
            ) from exc

        print(f"Wrote {destination}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synthesize chapter SSML batch to per-section per-language MP3 files."
    )
    parser.add_argument("ssml_file", type=Path, help="Path to the batch SSML file")
    parser.add_argument(
        "--env-file", type=Path, default=DEFAULT_ENV_FILE,
        help=f"Path to env.sh (default: {DEFAULT_ENV_FILE})",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate without calling Azure Speech",
    )
    parser.add_argument(
        "--insecure", action="store_true",
        help="Disable TLS certificate verification",
    )
    args = parser.parse_args()

    try:
        settings = load_settings(args.env_file, args.insecure)
        return synthesize_segments(
            args.ssml_file.resolve(),
            args.output_dir.resolve(),
            settings,
            args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
