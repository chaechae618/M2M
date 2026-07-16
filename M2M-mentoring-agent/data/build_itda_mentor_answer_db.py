"""
Build an Agent2 retrieval DB from the 140 real Itda Q&A rows.

Default behavior is safe:
  - reads ../../example_data.csv
  - writes json_db/mentor_answers_itda_140.json
  - writes data/cleaned/itda_mentor_answer_db_report.json
  - does NOT replace json_db/mentor_answers.json unless --install is passed

Examples:
  venv\\Scripts\\python.exe data\\build_itda_mentor_answer_db.py --no-embeddings
  venv\\Scripts\\python.exe data\\build_itda_mentor_answer_db.py
  venv\\Scripts\\python.exe data\\build_itda_mentor_answer_db.py --install
  venv\\Scripts\\python.exe data\\build_itda_mentor_answer_db.py --install --rebuild
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
DEFAULT_INPUT = PROJECT_ROOT / "example_data.csv"
DB_DIR = ROOT / "json_db"
DEFAULT_OUTPUT = DB_DIR / "mentor_answers_itda_140.json"
REPORT_OUTPUT = ROOT / "data" / "cleaned" / "itda_mentor_answer_db_report.json"
PRODUCTION_DB = DB_DIR / "mentor_answers.json"


def normalize_text(value: Any) -> str:
    text = str(value or "").replace("\ufeff", "").replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]

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


def get_field(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row:
            return normalize_text(row.get(name, ""))
    return ""


def summarize_answer(answer: str, limit: int = 220) -> str:
    for line in answer.split("\n"):
        stripped = line.strip()
        if len(stripped) >= 20:
            return stripped[:limit]
    return answer[:limit]


def split_tags(value: str) -> list[str]:
    value = normalize_text(value)
    if not value:
        return []
    parts = re.split(r"[/,>|]+", value)
    tags = [part.strip() for part in parts if part.strip()]
    return tags or [value]


def infer_situation_tags(question: str, title: str, answer: str) -> list[str]:
    text = f"{title}\n{question}\n{answer[:600]}"
    keyword_map = {
        "취업준비": ["취업", "취준", "지원", "입사", "채용"],
        "이직": ["이직", "전환", "커리어 전환", "직무 변경"],
        "자소서": ["자소서", "자기소개서", "지원서"],
        "면접": ["면접", "인터뷰", "PT 면접"],
        "포트폴리오": ["포트폴리오", "프로젝트", "성과"],
        "스펙": ["스펙", "자격증", "어학", "영어", "학벌"],
        "직무탐색": ["직무", "역량", "무슨 일을", "하는 일"],
        "현직자관점": ["현직", "실무", "업계", "회사"],
    }
    tags: list[str] = []
    for tag, keywords in keyword_map.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags


def infer_answer_scope(question: str, title: str, answer: str) -> str:
    text = f"{title}\n{question}\n{answer[:800]}"
    if any(word in text for word in ["봐주세요", "첨삭", "검토", "평가", "가능할까요", "괜찮을까요"]):
        return "experience_based"
    if any(word in text for word in ["차이", "무엇", "준비 방법", "필요", "역량", "구성"]):
        return "general_advice"
    return "experience_based"


def infer_personalization_level(question: str) -> str:
    high_markers = ["제 ", "제가", "저는", "저의", "가능할까요", "괜찮을까요", "봐주세요", "첨삭", "평가"]
    medium_markers = ["비전공", "전환", "이직", "포트폴리오", "자소서", "면접"]
    if any(marker in question for marker in high_markers):
        return "high"
    if any(marker in question for marker in medium_markers):
        return "medium"
    return "low"


def build_embedding_text(record: dict[str, Any]) -> str:
    return "\n".join(
        part
        for part in [
            f"질문 제목: {record['question_content']}",
            f"멘티 질문: {record['_mentee_question']}",
            f"답변 요약: {record['answer_summarize']}",
            f"분야: {', '.join(record['domain_tags'])}",
            f"상황: {', '.join(record['situation_tags'])}",
        ]
        if part.strip()
    )


def load_embedding_function():
    sys.path.insert(0, str(ROOT))
    from utils.env import load_project_env
    from utils.embedding import get_embedding

    load_project_env()
    return get_embedding


def read_csv_rows(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_record(row: dict[str, str], index: int, get_embedding=None) -> tuple[dict[str, Any] | None, str | None]:
    number = get_field(row, "번호", "number", "id")
    domain = get_field(row, "분야", "domain")
    title = get_field(row, "주제", "title")
    case_name = get_field(row, "case", "케이스")
    question = get_field(row, "멘티질문", "mentee_question", "question")
    answer = get_field(row, "멘토답변", "mentor_answer", "answer")
    source = get_field(row, "Source", "source") or "itda"

    if not question or not answer:
        return None, "missing_question_or_answer"

    source_number = re.sub(r"\D+", "", number) or f"{index:03d}"
    answer_id = f"itda_{int(source_number):03d}" if source_number.isdigit() else f"itda_{index:03d}"
    question_title = title or question[:80]
    answer_summary = summarize_answer(answer)

    record: dict[str, Any] = {
        "answer_id": answer_id,
        "session_id": f"itda_case_{answer_id.removeprefix('itda_')}",
        "mentor_id": "itda_mentor_unknown",
        "question_content": question_title,
        "answer_content": answer,
        "answer_summarize": answer_summary,
        "domain_tags": split_tags(domain),
        "situation_tags": infer_situation_tags(question, question_title, answer),
        "answer_scope": infer_answer_scope(question, question_title, answer),
        "personalization_level": infer_personalization_level(question),
        "source": "itda_140",
        "source_row": index,
        "source_number": number,
        "source_case": case_name,
        "source_name": source,
        "embedding_model": "text-embedding-3-small",
        "embedding_text": "",
        "embedding": None,
        "is_assetized": True,
        "reuse_count": 0,
        "satisfaction_score": None,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "_case_id": answer_id.upper(),
        "_case_title": question_title,
        "_mentee_question": question,
    }
    record["embedding_text"] = build_embedding_text(record)

    if get_embedding is not None:
        record["embedding"] = get_embedding(record["embedding_text"])

    return record, None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def backup_and_install(output_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = PRODUCTION_DB.with_name(f"mentor_answers.backup_{timestamp}.json")
    if PRODUCTION_DB.exists():
        shutil.copy2(PRODUCTION_DB, backup_path)
    shutil.copy2(output_path, PRODUCTION_DB)
    return backup_path


def output_has_complete_embeddings(output_path: Path) -> bool:
    if not output_path.exists():
        return False
    data = json.loads(output_path.read_text(encoding="utf-8"))
    records = data.get("records", [])
    return bool(records) and all(record.get("embedding") for record in records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=140)
    parser.add_argument("--no-embeddings", action="store_true", help="Build records without calling OpenAI embeddings.")
    parser.add_argument("--install", action="store_true", help="Replace json_db/mentor_answers.json after creating a backup.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild output even when --install can reuse an existing complete DB.")
    args = parser.parse_args()

    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    output_path = args.output if args.output.is_absolute() else ROOT / args.output

    if args.install and not args.rebuild and output_has_complete_embeddings(output_path):
        backup_path = backup_and_install(output_path)
        report = {
            "mode": "install_existing",
            "output": str(output_path),
            "installed_to": str(PRODUCTION_DB),
            "backup_path": str(backup_path),
            "message": "Installed existing DB because it already has complete embeddings. Pass --rebuild to regenerate embeddings.",
        }
        write_json(REPORT_OUTPUT, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    rows = read_csv_rows(input_path)
    if args.limit:
        rows = rows[: args.limit]

    get_embedding = None if args.no_embeddings else load_embedding_function()

    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        record, skip_reason = build_record(row, index, get_embedding=get_embedding)
        if record is None:
            skipped.append({"source_row": index, "reason": skip_reason})
            continue
        records.append(record)

    payload = {
        "schema_name": "mentor_answers",
        "version": "itda_140_v1",
        "description": "Agent2 retrieval DB generated from 140 real Itda Q&A rows.",
        "records": records,
    }
    write_json(output_path, payload)

    report = {
        "input": str(input_path),
        "output": str(output_path),
        "row_count": len(rows),
        "record_count": len(records),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "embedding_enabled": not args.no_embeddings,
        "embedding_count": sum(1 for record in records if record.get("embedding")),
        "domain_counts": dict(Counter(tag for record in records for tag in record.get("domain_tags", []))),
        "situation_counts": dict(Counter(tag for record in records for tag in record.get("situation_tags", []))),
        "answer_scope_counts": dict(Counter(record.get("answer_scope", "") for record in records)),
        "personalization_counts": dict(Counter(record.get("personalization_level", "") for record in records)),
    }
    if args.install:
        report["installed_to"] = str(PRODUCTION_DB)
        report["backup_path"] = str(backup_and_install(output_path))

    write_json(REPORT_OUTPUT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
