"""
Runtime CONFLARE-style calibration for Agent2.

Unlike calibrate_agent2_conformal_retrieval.py, this script uses the exact query
text that evaluate_agent2_baseline.py passes to SearchVerifyAgent:

    search_query = case["query"]

This avoids calibrating on a different embedding distribution.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.embedding import get_embedding, top_k_similar  # noqa: E402


DATASET_JSON = ROOT / "eval" / "agent2_balanced_with_direct_supplement.json"
ASSET_JSON = ROOT / "data" / "cleaned" / "example_qa_asset_candidates.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_runtime_conformal_calibration.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def quantile_cutoff(values: list[float], alpha: float) -> float:
    ordered = sorted(values)
    idx = max(0, math.ceil(alpha * len(ordered)) - 1)
    return ordered[idx]


def coverage(values: list[float], threshold: float) -> float:
    return sum(1 for value in values if value >= threshold) / len(values) if values else 0.0


def describe(values: list[float]) -> dict:
    ordered = sorted(values)
    out = {
        "count": len(ordered),
        "min": round(ordered[0], 6) if ordered else None,
        "max": round(ordered[-1], 6) if ordered else None,
    }
    for q in [0.01, 0.05, 0.10, 0.20, 0.50]:
        if not ordered:
            out[f"q{int(q * 100):02d}"] = None
            continue
        idx = max(0, math.ceil(q * len(ordered)) - 1)
        out[f"q{int(q * 100):02d}"] = round(ordered[idx], 6)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT.parent / ".env")
    load_dotenv(ROOT.parent / ".env.local")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required.")

    dataset = load_json(DATASET_JSON)
    cases = dataset.get("cases", [])
    if args.limit is not None:
        cases = cases[: args.limit]
    assets = [asset for asset in load_json(ASSET_JSON).get("records", []) if asset.get("embedding")]
    asset_by_id = {asset.get("answer_id"): asset for asset in assets}

    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    existing_rows = {}
    if args.resume and output_path.exists():
        existing_rows = {
            row["case_id"]: row
            for row in load_json(output_path).get("runtime_scores", [])
        }

    rows = list(existing_rows.values())
    seen = set(existing_rows)
    for idx, case in enumerate(cases, start=1):
        case_id = case["case_id"]
        if case_id in seen:
            continue
        source_id = case.get("source_answer_id")
        if source_id not in asset_by_id:
            continue
        print(f"[runtime conformal {idx:03d}/{len(cases):03d}] {case_id}")
        query_vec = get_embedding(case["query"])
        top = top_k_similar(query_vec, assets, vec_field="embedding", k=len(assets))
        source_rank = None
        source_similarity = None
        top5 = []
        for rank, (asset, score) in enumerate(top, start=1):
            if rank <= 5:
                top5.append({
                    "answer_id": asset.get("answer_id"),
                    "rank": rank,
                    "similarity": round(score, 6),
                })
            if asset.get("answer_id") == source_id:
                source_rank = rank
                source_similarity = score
                break

        rows.append({
            "case_id": case_id,
            "gold_verdict": case.get("gold", {}).get("verdict"),
            "source_answer_id": source_id,
            "source_answer_rank": source_rank,
            "source_answer_similarity": round(source_similarity, 6) if source_similarity is not None else None,
            "top5": top5,
        })

        write_json(output_path, {
            "description": "Runtime CONFLARE calibration scores for Agent2.",
            "runtime_query_definition": "case['query'] exactly as used by evaluate_agent2_baseline.py",
            "runtime_scores": rows,
        })

    calibration_values = [
        row["source_answer_similarity"] for row in rows
        if str(row.get("case_id", "")).startswith("realqa_")
        and row.get("gold_verdict") == "partial_with_mentor_suggest"
        and isinstance(row.get("source_answer_similarity"), (int, float))
    ]

    alpha_results = {}
    for alpha in [0.01, 0.05, 0.10, 0.20]:
        threshold = quantile_cutoff(calibration_values, alpha)
        alpha_results[f"alpha_{alpha:g}"] = {
            "alpha": alpha,
            "threshold": round(threshold, 6),
            "empirical_calibration_coverage": round(coverage(calibration_values, threshold), 6),
            "recommended_eval_args": [
                "--sim-search-first", f"{threshold:.6f}",
                "--sim-mentor-first", f"{threshold:.6f}",
            ],
        }

    payload = {
        "description": "Runtime CONFLARE calibration scores for Agent2.",
        "runtime_query_definition": "case['query'] exactly as used by evaluate_agent2_baseline.py",
        "calibration_filter": {
            "case_id_prefix": "realqa_",
            "gold_verdict": "partial_with_mentor_suggest",
        },
        "distributions": {
            "runtime_realqa_partial": describe(calibration_values),
            "runtime_all_rows": describe([
                row["source_answer_similarity"] for row in rows
                if isinstance(row.get("source_answer_similarity"), (int, float))
            ]),
        },
        "alpha_results": alpha_results,
        "runtime_scores": rows,
    }
    write_json(output_path, payload)
    print(json.dumps({
        "output": str(output_path),
        "distributions": payload["distributions"],
        "alpha_results": alpha_results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
