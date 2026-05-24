#!/usr/bin/env python3
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

SPEECH_NS = "http://www.w3.org/2001/10/synthesis"
XML_NS = "http://www.w3.org/XML/1998/namespace"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = SCRIPT_DIR / "env.sh"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "audio"
ET.register_namespace("", SPEECH_NS)
OUTPUT_FORMATS = {
    "audio-16khz-32kbitrate-mono-mp3": "audio-16khz-32kbitrate-mono-mp3",
    "audio-16khz-64kbitrate-mono-mp3": "audio-16khz-64kbitrate-mono-mp3",
    "audio-24khz-48kbitrate-mono-mp3": "audio-24khz-48kbitrate-mono-mp3",
    "audio-24khz-96kbitrate-mono-mp3": "audio-24khz-96kbitrate-mono-mp3",
    "audio-48khz-96kbitrate-mono-mp3": "audio-48khz-96kbitrate-mono-mp3",
    "raw-16khz-16bit-mono-pcm": "raw-16khz-16bit-mono-pcm",
    "raw-24khz-16bit-mono-pcm": "raw-24khz-16bit-mono-pcm",
    "raw-48khz-16bit-mono-pcm": "raw-48khz-16bit-mono-pcm",
}


@dataclass(frozen=True)
class Settings:
    speech_key: str
    speech_region: str
    voice_de: str
    voice_ru: str
    output_format: str
    insecure_ssl: bool


def build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ModuleNotFoundError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def clone_element(element: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(element, encoding="unicode"))


def new_speak_root(template: ET.Element) -> ET.Element:
    root = ET.Element(template.tag, template.attrib)
    root.text = template.text
    root.tail = template.tail
    return root


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


def load_settings(env_file: Path) -> Settings:
    file_values = parse_env_file(env_file)

    def resolve(name: str) -> str:
        return os.environ.get(name) or file_values.get(name, "")

    settings = Settings(
        speech_key=resolve("SPEECH_KEY"),
        speech_region=resolve("SPEECH_REGION"),
        voice_de=resolve("TTS_VOICE_DE"),
        voice_ru=resolve("TTS_VOICE_RU"),
        output_format=resolve("TTS_OUTPUT_FORMAT") or "audio-24khz-96kbitrate-mono-mp3",
        insecure_ssl=resolve("TTS_INSECURE_SSL").lower() in {"1", "true", "yes", "on"},
    )

    missing = [
        name
        for name, value in (
            ("SPEECH_KEY", settings.speech_key),
            ("SPEECH_REGION", settings.speech_region),
            ("TTS_VOICE_DE", settings.voice_de),
            ("TTS_VOICE_RU", settings.voice_ru),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required configuration values: {joined}")
    if settings.output_format not in OUTPUT_FORMATS:
        supported = ", ".join(sorted(OUTPUT_FORMATS))
        raise ValueError(
            f"Unsupported TTS_OUTPUT_FORMAT '{settings.output_format}'. Supported values: {supported}"
        )
    return settings


def question_ssml_blocks(batch_file: Path, settings: Settings) -> list[tuple[str, list[str]]]:
    try:
        tree = ET.parse(batch_file)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid SSML batch file {batch_file}: {exc}") from exc

    root = tree.getroot()
    if root.tag != "tts-batch":
        raise ValueError("Root element must be <tts-batch>")

    blocks: list[tuple[str, list[str]]] = []
    lang_attribute = f"{{{XML_NS}}}lang"

    for question in root.findall("question"):
        number = (question.attrib.get("number") or "").strip()
        if not number:
            raise ValueError("Each <question> must define a non-empty number attribute")

        speak = next((child for child in question if local_name(child.tag) == "speak"), None)
        if speak is None:
            raise ValueError(f"Question {number} is missing a <speak> element")

        speak_copy = clone_element(speak)
        for voice in speak_copy.iter():
            if local_name(voice.tag) != "voice":
                continue
            xml_lang = voice.attrib.get(lang_attribute, "")
            if xml_lang.startswith("ru"):
                voice.set("name", settings.voice_ru)
            elif xml_lang.startswith("de"):
                voice.set("name", settings.voice_de)
            else:
                raise ValueError(
                    f"Question {number} contains a <voice> without xml:lang set to ru-* or de-*"
                )

        segments: list[str] = []
        current_root: ET.Element | None = None
        current_voice: ET.Element | None = None
        pending_nodes: list[ET.Element] = []

        for child in list(speak_copy):
            child_copy = clone_element(child)
            if local_name(child_copy.tag) == "voice":
                if current_root is not None:
                    segments.append(ET.tostring(current_root, encoding="unicode"))
                current_root = new_speak_root(speak_copy)
                current_voice = child_copy
                for pending in pending_nodes:
                    current_voice.append(clone_element(pending))
                pending_nodes = []
                current_root.append(current_voice)
                continue

            pending_nodes.append(child_copy)

        if current_root is not None:
            if current_voice is not None:
                for pending in pending_nodes:
                    current_voice.append(clone_element(pending))
            segments.append(ET.tostring(current_root, encoding="unicode"))

        if not segments:
            raise ValueError(f"Question {number} does not contain any <voice> segments")

        blocks.append((number, segments))

    if not blocks:
        raise ValueError("No <question> elements found in the SSML batch file")
    return blocks


def synthesize_batch(
    batch_file: Path,
    output_dir: Path,
    settings: Settings,
    dry_run: bool,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    blocks = question_ssml_blocks(batch_file, settings)
    endpoint = f"https://{settings.speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    ssl_context = ssl._create_unverified_context() if settings.insecure_ssl else build_ssl_context()

    if dry_run:
        for number, segments in blocks:
            print(f"DRY RUN {number} ({len(segments)} segments) -> {output_dir / f'{number}.mp3'}")
        return 0

    for number, segments in blocks:
        destination = output_dir / f"{number}.mp3"
        audio_parts: list[bytes] = []

        for index, ssml in enumerate(segments, start=1):
            request = urllib.request.Request(
                endpoint,
                data=ssml.encode("utf-8"),
                headers={
                    "Content-Type": "application/ssml+xml",
                    "Ocp-Apim-Subscription-Key": settings.speech_key,
                    "X-Microsoft-OutputFormat": OUTPUT_FORMATS[settings.output_format],
                    "User-Agent": "boot-binnen-motor-tts",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(request, timeout=120, context=ssl_context) as response:
                    audio_parts.append(response.read())
            except urllib.error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Synthesis failed for question {number}, segment {index}: HTTP {exc.code} - {details}"
                ) from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(
                    f"Synthesis failed for question {number}, segment {index}: {exc.reason}"
                ) from exc

        destination.write_bytes(b"".join(audio_parts))
        print(f"Wrote {destination}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate one MP3 per <question> entry from a batch SSML file."
    )
    parser.add_argument("ssml_file", type=Path, help="Path to the batch SSML input file")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f"Path to env.sh style configuration file (default: {DEFAULT_ENV_FILE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for generated MP3 files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and input parsing without calling Azure Speech",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for this run. Use only if your local trust store is broken.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        settings = load_settings(args.env_file)
        if args.insecure:
            settings = Settings(
                speech_key=settings.speech_key,
                speech_region=settings.speech_region,
                voice_de=settings.voice_de,
                voice_ru=settings.voice_ru,
                output_format=settings.output_format,
                insecure_ssl=True,
            )
        return synthesize_batch(
            batch_file=args.ssml_file.resolve(),
            output_dir=args.output_dir.resolve(),
            settings=settings,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
