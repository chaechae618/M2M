"""
Clean example_data.csv into validation-ready Q&A records.

Inputs:
  ../../example_data.csv

Outputs:
  data/cleaned/example_qa_clean.csv
  data/cleaned/example_qa_clean.json
  data/cleaned/example_qa_clean_report.json
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
INPUT_PATH = PROJECT_ROOT / "example_data.csv"
OUTPUT_DIR = ROOT / "data" / "cleaned"
OUTPUT_CSV = OUTPUT_DIR / "example_qa_clean.csv"
OUTPUT_JSON = OUTPUT_DIR / "example_qa_clean.json"
REPORT_JSON = OUTPUT_DIR / "example_qa_clean_report.json"


DOMAIN_MAP = {
    "회계/재무/금융": "회계/재무/금융",
    "마케팅/md": "마케팅/MD",
    "마케팅/MD": "마케팅/MD",
    "IT 개발, 데이터": "IT개발/데이터",
    "IT개발/데이터": "IT개발/데이터",
    "홍보/CSR": "홍보/CSR",
    "전략/기획": "전략/기획",
    "영업/영업관리": "영업/영업관리",
    "유통/무역/구매": "유통/무역/구매",
    "디자인/예술": "디자인/예술",
    "생산/품질/제조": "생산/품질/제조",
    "연구/설계": "연구/설계",
}

COPYRIGHT_PATTERNS = [
    r"©\s*모든 저작권은[\s\S]*$",
    r"ⓒ\s*모든 저작권은[\s\S]*$",
]

PRIVACY_PATTERNS = {
    "phone": re.compile(r"\b\d{2,3}-\d{3,4}-\d{4}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}"),
    "student_id": re.compile(r"\d{2,4}\s*학번"),
}


def normalize_text(value: str) -> str:
    text = (value or "").replace("\ufeff", "").replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern in COPYRIGHT_PATTERNS:
        text = re.sub(pattern, "", text).strip()
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if re.match(r"^[©ⓒ]\s*[\w .,'&-]{2,80}$", line):
            continue
        lines.append(line)

    normalized: list[str] = []
    blank_pending = False
    for line in lines:
        if not line:
            blank_pending = bool(normalized)
            continue
        if blank_pending:
            normalized.append("")
            blank_pending = False
        normalized.append(line)
    return "\n".join(normalized).strip()


def normalize_domain(value: str) -> str:
    raw = normalize_text(value)
    return DOMAIN_MAP.get(raw, raw or "미분류")


def make_record_id(number: str, case: str, index: int) -> str:
    number_part = re.sub(r"\D+", "", number or "")
    if number_part:
        return f"realqa_{int(number_part):03d}"
    case_part = re.sub(r"[^0-9A-Za-z가-힣]+", "_", case or "").strip("_").lower()
    if case_part:
        return f"realqa_{case_part}"
    return f"realqa_row_{index:03d}"


def privacy_flags(*texts: str) -> list[str]:
    combined = "\n".join(texts)
    return [name for name, pattern in PRIVACY_PATTERNS.items() if pattern.search(combined)]


def summarize_answer(answer: str, limit: int = 180) -> str:
    for line in answer.split("\n"):
        stripped = line.strip()
        if len(stripped) >= 20:
            return stripped[:limit]
    return answer[:limit]


def read_rows() -> list[dict]:
    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    cleaned: list[dict] = []
    skipped: list[dict] = []
    seen_ids: Counter[str] = Counter()

    for index, row in enumerate(rows, start=1):
        question = normalize_text(row.get("멘티질문", ""))
        answer = normalize_text(row.get("멘토답변", ""))
        title = normalize_text(row.get("주제", ""))
        domain = normalize_domain(row.get("분야", ""))
        case = normalize_text(row.get("case", ""))
        number = normalize_text(row.get("번호", ""))

        if not question or not answer:
            skipped.append({
                "source_row": index,
                "number": number,
                "case": case,
                "reason": "missing_question_or_answer",
            })
            continue

        record_id = make_record_id(number, case, index)
        seen_ids[record_id] += 1
        if seen_ids[record_id] > 1:
            record_id = f"{record_id}_{seen_ids[record_id]}"

        cleaned.append({
            "record_id": record_id,
            "source_row": index,
            "original_number": number,
            "domain": domain,
            "title": title,
            "case": case,
            "mentee_question": question,
            "mentor_answer": answer,
            "answer_summary": summarize_answer(answer),
            "question_char_len": len(question),
            "answer_char_len": len(answer),
            "privacy_flags": privacy_flags(question, answer),
        })

    report = {
        "input_path": str(INPUT_PATH),
        "input_rows": len(rows),
        "clean_rows": len(cleaned),
        "skipped_rows": len(skipped),
        "skipped": skipped,
        "domain_counts": dict(Counter(r["domain"] for r in cleaned).most_common()),
        "privacy_flag_counts": dict(Counter(flag for r in cleaned for flag in r["privacy_flags"])),
        "min_question_len": min((r["question_char_len"] for r in cleaned), default=0),
        "max_question_len": max((r["question_char_len"] for r in cleaned), default=0),
        "min_answer_len": min((r["answer_char_len"] for r in cleaned), default=0),
        "max_answer_len": max((r["answer_char_len"] for r in cleaned), default=0),
    }
    return cleaned, report


def write_outputs(records: list[dict], report: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "record_id",
        "source_row",
        "original_number",
        "domain",
        "title",
        "case",
        "mentee_question",
        "mentor_answer",
        "answer_summary",
        "question_char_len",
        "answer_char_len",
        "privacy_flags",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["privacy_flags"] = "|".join(row["privacy_flags"])
            writer.writerow(row)

    OUTPUT_JSON.write_text(
        json.dumps({"records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    rows = read_rows()
    records, report = clean_rows(rows)
    write_outputs(records, report)
    print(json.dumps({
        "clean_rows": report["clean_rows"],
        "skipped_rows": report["skipped_rows"],
        "output_csv": str(OUTPUT_CSV),
        "output_json": str(OUTPUT_JSON),
        "report_json": str(REPORT_JSON),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
