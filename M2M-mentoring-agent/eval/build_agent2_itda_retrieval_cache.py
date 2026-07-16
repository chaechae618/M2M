"""
Build reusable query-embedding and retrieval cache for Agent2 Itda experiments.

This makes one embedding call per unique query, then computes similarities
against the local mentor_answers DB. Threshold experiments can reuse this file
instead of calling the embedding API for every grid-search run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.embedding import cosine_similarity, get_embedding  # noqa: E402


VALIDATION_JSON = ROOT / "eval" / "agent2_itda_validation.json"
EVAL_JSON = ROOT / "eval" / "agent2_itda_eval.json"
ASSETS_JSON = ROOT / "json_db" / "mentor_answers.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_itda_retrieval_cache.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_env_files() -> None:
    for path in [ROOT / ".env", ROOT / ".env.local", ROOT.parent / ".env", ROOT.parent / ".env.local"]:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def case_rows(dataset_paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for path in dataset_paths:
        data = load_json(path)
        split_name = path.stem
        for case in data.get("cases", []):
            if case["case_id"] in seen:
                continue
            seen.add(case["case_id"])
            rows.append({**case, "_split_source": split_name})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="*", type=Path, default=[VALIDATION_JSON, EVAL_JSON])
    parser.add_argument("--assets", type=Path, default=ASSETS_JSON)
    parser.add_argument("--output", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--top-n", type=int, default=140)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    load_env_files()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required.")

    dataset_paths = [path if path.is_absolute() else ROOT / path for path in args.datasets]
    assets_path = args.assets if args.assets.is_absolute() else ROOT / args.assets
    output_path = args.output if args.output.is_absolute() else ROOT / args.output

    assets = [asset for asset in load_json(assets_path).get("records", []) if asset.get("embedding")]
    assets_by_id = {asset["answer_id"]: asset for asset in assets}

    existing: dict[str, Any] = {}
    if args.resume and output_path.exists():
        existing_data = load_json(output_path)
        existing = {row["case_id"]: row for row in existing_data.get("cases", [])}

    cached_cases = []
    for idx, case in enumerate(case_rows(dataset_paths), start=1):
        if case["case_id"] in existing:
            cached_cases.append(existing[case["case_id"]])
            print(f"[cache skip {idx:03d}] {case['case_id']}")
            continue

        print(f"[cache build {idx:03d}] {case['case_id']} subtype={case.get('gold', {}).get('subtype')}")
        query_embedding = get_embedding(case["query"])
        scored = []
        for asset in assets:
            score = cosine_similarity(query_embedding, asset["embedding"])
            scored.append({
                "answer_id": asset["answer_id"],
                "similarity": round(score, 6),
            })
        scored.sort(key=lambda row: row["similarity"], reverse=True)

        cached = {
            "case_id": case["case_id"],
            "query": case["query"],
            "gold": case.get("gold", {}),
            "domain": case.get("domain", ""),
            "query_embedding": query_embedding,
            "top": scored[: args.top_n],
            "split_source": case.get("_split_source", ""),
        }
        cached_cases.append(cached)
        write_json(output_path, {
            "description": "Query embedding and retrieval cache for Agent2 Itda experiments.",
            "assets": str(assets_path),
            "asset_count": len(assets),
            "asset_ids": list(assets_by_id),
            "cases": cached_cases,
        })

    payload = {
        "description": "Query embedding and retrieval cache for Agent2 Itda experiments.",
        "assets": str(assets_path),
        "asset_count": len(assets),
        "asset_ids": list(assets_by_id),
        "cases": cached_cases,
    }
    write_json(output_path, payload)
    print(json.dumps({
        "output": str(output_path),
        "case_count": len(cached_cases),
        "asset_count": len(assets),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
