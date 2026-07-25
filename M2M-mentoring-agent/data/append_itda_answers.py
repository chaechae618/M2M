"""
기존 mentor_answers.json(Agent2 검색 DB)에 새 Q&A CSV를 추가(append)한다.

build_itda_mentor_answer_db.py와 달리 production DB를 덮어쓰지 않고
기존 레코드 뒤에 새 레코드를 이어붙인다. answer_id가 겹치면 중단한다.

실행:
  venv\\Scripts\\python.exe data\\append_itda_answers.py --input "새파일.csv"
  venv\\Scripts\\python.exe data\\append_itda_answers.py --input "새파일.csv" --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.build_itda_mentor_answer_db import build_record, read_csv_rows, load_embedding_function  # noqa: E402

PRODUCTION_DB = ROOT / "json_db" / "mentor_answers.json"
REPORT_OUTPUT = ROOT / "data" / "cleaned" / "append_itda_answers_report.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--no-embeddings", action="store_true", help="임베딩 없이 레코드만 생성 (검증용)")
    parser.add_argument("--dry-run", action="store_true", help="production DB에 쓰지 않고 결과만 리포트")
    args = parser.parse_args()

    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    if not input_path.exists():
        print(f"입력 파일을 찾을 수 없음: {input_path}")
        sys.exit(1)

    production = json.loads(PRODUCTION_DB.read_text(encoding="utf-8"))
    existing_ids = {r["answer_id"] for r in production["records"]}

    rows = read_csv_rows(input_path)
    get_embedding = None if args.no_embeddings else load_embedding_function()

    new_records: list[dict] = []
    skipped: list[dict] = []
    for index, row in enumerate(rows, start=1):
        record, skip_reason = build_record(row, index, get_embedding=get_embedding)
        if record is None:
            skipped.append({"source_row": index, "reason": skip_reason})
            continue
        if record["answer_id"] in existing_ids:
            skipped.append({"source_row": index, "reason": f"id_collision:{record['answer_id']}"})
            continue
        new_records.append(record)
        existing_ids.add(record["answer_id"])

    report = {
        "input": str(input_path),
        "existing_count_before": len(production["records"]),
        "new_row_count": len(rows),
        "appended_count": len(new_records),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "embedding_enabled": not args.no_embeddings,
        "embedding_count": sum(1 for r in new_records if r.get("embedding")),
        "domain_counts": dict(Counter(tag for r in new_records for tag in r.get("domain_tags", []))),
        "total_after": len(production["records"]) + len(new_records) if not args.dry_run else None,
    }

    if args.dry_run:
        report["mode"] = "dry_run_no_write"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = PRODUCTION_DB.with_name(f"mentor_answers.backup_{timestamp}.json")
    shutil.copy2(PRODUCTION_DB, backup_path)

    production["records"].extend(new_records)
    PRODUCTION_DB.write_text(json.dumps(production, ensure_ascii=False, indent=2), encoding="utf-8")

    report["mode"] = "appended"
    report["backup_path"] = str(backup_path)
    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
