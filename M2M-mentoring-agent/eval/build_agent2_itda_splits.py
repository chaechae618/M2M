"""
Build stratified Agent2 validation/eval splits for the Itda-140 DB experiment.

Inputs:
  D:/ai rookie/generate_data/agent2_llm_direct_db_100.csv
  D:/ai rookie/generate_data/agent2_llm_direct_general_100.csv
  D:/ai rookie/generate_data/agent2_mentor_needed_200.csv

Outputs:
  eval/agent2_itda_validation.json
  eval/agent2_itda_eval.json
  eval/agent2_itda_split_report.json

The task is binary for this experiment:
  - llm_direct
  - mentor_needed

Agent2 may internally predict partial_with_mentor_suggest, but evaluation can
collapse that into mentor_needed because the product requirement is:
"anything that cannot be solved as llm_direct should fall back to mentor".
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
GENERATE_DIR = ROOT.parent.parent / "generate_data"

SOURCES = [
    (
        GENERATE_DIR / "agent2_llm_direct_db_100.csv",
        "llm_direct",
        "llm_direct_db",
    ),
    (
        GENERATE_DIR / "agent2_llm_direct_general_100.csv",
        "llm_direct",
        "llm_direct_general",
    ),
    (
        GENERATE_DIR / "agent2_mentor_needed_200.csv",
        "mentor_needed",
        "mentor_needed",
    ),
]

VALIDATION_JSON = ROOT / "eval" / "agent2_itda_validation.json"
EVAL_JSON = ROOT / "eval" / "agent2_itda_eval.json"
REPORT_JSON = ROOT / "eval" / "agent2_itda_split_report.json"


def read_csv(path: Path, gold_label: str, subtype: str) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    cases = []
    for idx, row in enumerate(rows, start=1):
        query = (row.get("query") or "").strip()
        if not query:
            continue
        case_id = (row.get("test_id") or f"{subtype}_{idx:03d}").strip()
        cases.append({
            "case_id": case_id,
            "query": query,
            "domain": (row.get("domain") or "").strip(),
            "career_stage": (row.get("career_stage") or "").strip(),
            "major": (row.get("major") or "").strip(),
            "constraint": (row.get("constraint") or "").strip(),
            "generation_reason": (row.get("generation_reason") or "").strip(),
            "generation_method": (row.get("generation_method") or "").strip(),
            "gold": {
                "verdict": gold_label,
                "subtype": subtype,
            },
        })
    return cases


def split_cases(cases: list[dict[str, Any]], validation_ratio: float, rng: random.Random) -> tuple[list[dict], list[dict]]:
    shuffled = list(cases)
    rng.shuffle(shuffled)
    validation_count = round(len(shuffled) * validation_ratio)
    return shuffled[:validation_count], shuffled[validation_count:]


def counts(cases: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        "label": dict(Counter(case["gold"]["verdict"] for case in cases)),
        "subtype": dict(Counter(case["gold"]["subtype"] for case in cases)),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-ratio", type=float, default=0.8)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    validation_cases: list[dict[str, Any]] = []
    eval_cases: list[dict[str, Any]] = []
    source_report = []

    for path, gold_label, subtype in SOURCES:
        cases = read_csv(path, gold_label, subtype)
        val, ev = split_cases(cases, args.validation_ratio, rng)
        validation_cases.extend(val)
        eval_cases.extend(ev)
        source_report.append({
            "path": str(path),
            "subtype": subtype,
            "gold_label": gold_label,
            "total": len(cases),
            "validation": len(val),
            "eval": len(ev),
        })

    rng.shuffle(validation_cases)
    rng.shuffle(eval_cases)

    validation_payload = {
        "description": "Agent2 Itda-140 validation split for threshold selection.",
        "task": "binary_llm_direct_vs_mentor_needed",
        "prediction_collapse": {
            "llm_direct": "llm_direct",
            "partial_with_mentor_suggest": "mentor_needed",
            "mentor_needed": "mentor_needed",
        },
        "cases": validation_cases,
    }
    eval_payload = {
        "description": "Agent2 Itda-140 held-out eval split for final fixed-threshold evaluation.",
        "task": "binary_llm_direct_vs_mentor_needed",
        "prediction_collapse": validation_payload["prediction_collapse"],
        "cases": eval_cases,
    }
    report = {
        "seed": args.seed,
        "validation_ratio": args.validation_ratio,
        "sources": source_report,
        "validation_counts": counts(validation_cases),
        "eval_counts": counts(eval_cases),
        "validation_json": str(VALIDATION_JSON),
        "eval_json": str(EVAL_JSON),
    }

    write_json(VALIDATION_JSON, validation_payload)
    write_json(EVAL_JSON, eval_payload)
    write_json(REPORT_JSON, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
