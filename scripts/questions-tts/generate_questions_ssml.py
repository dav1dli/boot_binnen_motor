#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "questions.json"
DEFAULT_OUTPUT = ROOT / "data" / "questions-tts" / "questions-all-tts.xml"
SPEECH_NS = "http://www.w3.org/2001/10/synthesis"
XML_NS = "http://www.w3.org/XML/1998/namespace"
RU_VOICE = "ru-RU-DmitryNeural"
DE_VOICE = "de-DE-Florian:DragonHDLatestNeural"

SPACE_RE = re.compile(r"\s+")
EMPTY_PARENS_RE = re.compile(r"\(\s*\)")
PARENS_CONTENT_RE = re.compile(r"\(([^()]+)\)")
RANGE_RE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")
DECIMAL_PERMILLE_RE = re.compile(r"(\d+)([.,])(\d+)\s*‰")
DECIMAL_RE = re.compile(r"(\d+)([.,])(\d+)")
DEGREE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*°")


RU_UNITS = {
    "0": "ноль",
    "1": "один",
    "2": "два",
    "3": "три",
    "4": "четыре",
    "5": "пять",
    "6": "шесть",
    "7": "семь",
    "8": "восемь",
    "9": "девять",
    "10": "десять",
    "11": "одиннадцать",
    "12": "двенадцать",
    "13": "тринадцать",
    "14": "четырнадцать",
    "15": "пятнадцать",
    "16": "шестнадцать",
    "17": "семнадцать",
    "18": "восемнадцать",
    "19": "девятнадцать",
}


DE_UNITS = {
    "0": "null",
    "1": "eins",
    "2": "zwei",
    "3": "drei",
    "4": "vier",
    "5": "fünf",
    "6": "sechs",
    "7": "sieben",
    "8": "acht",
    "9": "neun",
    "10": "zehn",
    "11": "elf",
    "12": "zwölf",
    "13": "dreizehn",
    "14": "vierzehn",
    "15": "fünfzehn",
    "16": "sechzehn",
    "17": "siebzehn",
    "18": "achtzehn",
    "19": "neunzehn",
}


def digit_word(lang: str, value: str) -> str:
    if lang == "ru":
        return RU_UNITS.get(value, value)
    return DE_UNITS.get(value, value)


def decimal_spoken(lang: str, integer: str, fraction: str) -> str:
    if lang == "ru":
        denominator = {
            1: "десятых",
            2: "сотых",
            3: "тысячных",
        }.get(len(fraction), "долей")
        return f"{digit_word(lang, integer)} целых {digit_word(lang, fraction)} {denominator}"
    fraction_words = " ".join(digit_word(lang, ch) for ch in fraction)
    return f"{digit_word(lang, integer)} Komma {fraction_words}"


def best_answer_text(question: dict, lang: str) -> str:
    answers = question[lang]["answers"]
    preferred_index = choose_correct_index(question, lang)
    candidates = [preferred_index, *range(len(answers))]
    for index in candidates:
        if 0 <= index < len(answers):
            answer = SPACE_RE.sub(" ", answers[index]).strip()
            if answer:
                return answer
    return "Ответ отсутствует" if lang == "ru" else "Antwort fehlt"


def replace_parenthetical_aliases(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        inner = SPACE_RE.sub(" ", match.group(1)).strip()
        if not inner:
            return ""
        if all(ch in "*-./ " for ch in inner):
            return f" {inner}"
        return f", {inner}"

    return PARENS_CONTENT_RE.sub(repl, value)


def normalize_text(text: str, lang: str) -> str:
    value = SPACE_RE.sub(" ", text).strip()
    value = EMPTY_PARENS_RE.sub("", value)
    value = replace_parenthetical_aliases(value)
    value = DECIMAL_PERMILLE_RE.sub(
        lambda match: f"{decimal_spoken(lang, match.group(1), match.group(3))} {'промилле' if lang == 'ru' else 'Promille'}",
        value,
    )
    value = RANGE_RE.sub(
        lambda match: f"от {match.group(1)} до {match.group(2)}"
        if lang == "ru"
        else f"{digit_word(lang, match.group(1))} bis {digit_word(lang, match.group(2))}",
        value,
    )
    value = DEGREE_RE.sub(
        lambda match: f"{match.group(1)} {'градусов' if lang == 'ru' else 'Grad'}",
        value,
    )
    value = DECIMAL_RE.sub(
        lambda match: decimal_spoken(lang, match.group(1), match.group(3)),
        value,
    )
    value = re.sub(r"\s+([,.;:?!])", r"\1", value)
    value = value.replace("?,", ",")
    value = re.sub(r"^Около\s+от\s+", "От ", value)
    value = SPACE_RE.sub(" ", value).strip()
    if value and value[-1] not in ".!?":
        value += "."
    return value


def spoken_number_ru(number: int) -> str:
    units = {
        0: "ноль",
        1: "один",
        2: "два",
        3: "три",
        4: "четыре",
        5: "пять",
        6: "шесть",
        7: "семь",
        8: "восемь",
        9: "девять",
        10: "десять",
        11: "одиннадцать",
        12: "двенадцать",
        13: "тринадцать",
        14: "четырнадцать",
        15: "пятнадцать",
        16: "шестнадцать",
        17: "семнадцать",
        18: "восемнадцать",
        19: "девятнадцать",
    }
    tens = {
        20: "двадцать",
        30: "тридцать",
        40: "сорок",
        50: "пятьдесят",
        60: "шестьдесят",
        70: "семьдесят",
        80: "восемьдесят",
        90: "девяносто",
    }
    hundreds = {
        100: "сто",
        200: "двести",
        300: "триста",
        400: "четыреста",
        500: "пятьсот",
        600: "шестьсот",
        700: "семьсот",
        800: "восемьсот",
        900: "девятьсот",
    }
    if number < 20:
        return units[number]
    if number < 100:
        tens_value = number // 10 * 10
        remainder = number % 10
        return tens[tens_value] if remainder == 0 else f"{tens[tens_value]} {units[remainder]}"
    hundreds_value = number // 100 * 100
    remainder = number % 100
    return hundreds[hundreds_value] if remainder == 0 else f"{hundreds[hundreds_value]} {spoken_number_ru(remainder)}"


def spoken_number_de(number: int) -> str:
    units = {
        0: "null",
        1: "eins",
        2: "zwei",
        3: "drei",
        4: "vier",
        5: "fünf",
        6: "sechs",
        7: "sieben",
        8: "acht",
        9: "neun",
        10: "zehn",
        11: "elf",
        12: "zwölf",
        13: "dreizehn",
        14: "vierzehn",
        15: "fünfzehn",
        16: "sechzehn",
        17: "siebzehn",
        18: "achtzehn",
        19: "neunzehn",
    }
    tens = {
        20: "zwanzig",
        30: "dreißig",
        40: "vierzig",
        50: "fünfzig",
        60: "sechzig",
        70: "siebzig",
        80: "achtzig",
        90: "neunzig",
    }
    if number < 20:
        return units[number]
    if number < 100:
        tens_value = number // 10 * 10
        remainder = number % 10
        if remainder == 0:
            return tens[tens_value]
        prefix = "ein" if remainder == 1 else units[remainder]
        return f"{prefix}und{tens[tens_value]}"
    hundreds_value = number // 100
    remainder = number % 100
    hundreds_text = "einhundert" if hundreds_value == 1 else f"{units[hundreds_value]}hundert"
    return hundreds_text if remainder == 0 else f"{hundreds_text}{spoken_number_de(remainder)}"


def choose_correct_index(question: dict, lang: str) -> int:
    answers = question[lang]["answers"]
    correct = question[lang].get("correct", -1)
    if 0 <= correct < len(answers):
        return correct

    de_correct = question["de"].get("correct", 0)
    if 0 <= de_correct < len(answers):
        return de_correct
    return 0


def build_question_element(question: dict) -> ET.Element:
    question_number = int(question["number"])
    number_attr = f"{question_number:03d}"
    ru_correct = choose_correct_index(question, "ru")
    de_correct = choose_correct_index(question, "de")

    question_el = ET.Element("question", {"number": number_attr})
    speak = ET.SubElement(
        question_el,
        "speak",
        {"version": "1.0", "xmlns": SPEECH_NS, f"{{{XML_NS}}}lang": "ru-RU"},
    )

    ru_voice = ET.SubElement(
        speak,
        "voice",
        {"name": RU_VOICE, f"{{{XML_NS}}}lang": "ru-RU"},
    )
    ru_paragraph = ET.SubElement(ru_voice, "p")
    for sentence in (
        f"Вопрос номер {spoken_number_ru(question_number)}.",
        normalize_text(question["ru"]["question"], "ru"),
        None,
        "Правильный ответ.",
        normalize_text(best_answer_text(question, "ru"), "ru"),
    ):
        if sentence is None:
            ET.SubElement(ru_paragraph, "break", {"time": "900ms"})
            continue
        sentence_el = ET.SubElement(ru_paragraph, "s")
        sentence_el.text = sentence

    ET.SubElement(speak, "break", {"time": "1300ms"})

    de_voice = ET.SubElement(
        speak,
        "voice",
        {"name": DE_VOICE, f"{{{XML_NS}}}lang": "de-DE"},
    )
    de_paragraph = ET.SubElement(de_voice, "p")
    for sentence in (
        f"Frage Nummer {spoken_number_de(question_number)}.",
        normalize_text(question["de"]["question"], "de"),
        None,
        "Richtige Antwort.",
        normalize_text(best_answer_text(question, "de"), "de"),
    ):
        if sentence is None:
            ET.SubElement(de_paragraph, "break", {"time": "900ms"})
            continue
        sentence_el = ET.SubElement(de_paragraph, "s")
        sentence_el.text = sentence

    return question_el


def build_batch(questions: list[dict]) -> ET.ElementTree:
    root = ET.Element("tts-batch")
    for question in questions:
        root.append(build_question_element(question))
    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    return tree


def filter_questions(
    questions: list[dict],
    chapter: str | None,
    from_number: int | None,
    to_number: int | None,
) -> list[dict]:
    filtered = questions
    if chapter:
        filtered = [question for question in filtered if str(question.get("chapter")) == chapter]
    if from_number is not None:
        filtered = [question for question in filtered if int(question["number"]) >= from_number]
    if to_number is not None:
        filtered = [question for question in filtered if int(question["number"]) <= to_number]
    return filtered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a full bilingual SSML batch directly from data/questions.json."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help=f"Input JSON file (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Output SSML batch file (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for preview generation")
    parser.add_argument("--chapter", type=str, help="Optional chapter filter, for example 11 or 11_1")
    parser.add_argument("--from-number", type=int, help="Optional inclusive lower bound for question number")
    parser.add_argument("--to-number", type=int, help="Optional inclusive upper bound for question number")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    questions = json.loads(args.input.read_text(encoding="utf-8"))
    questions = filter_questions(questions, args.chapter, args.from_number, args.to_number)
    if args.limit > 0:
        questions = questions[: args.limit]
    if not questions:
        raise SystemExit("No questions matched the provided filters")

    tree = build_batch(questions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {args.output} with {len(questions)} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())