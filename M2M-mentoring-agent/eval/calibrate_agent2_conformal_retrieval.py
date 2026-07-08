"""
Calibrate Agent2 retrieval thresholds with a CONFLARE-style conformal cutoff.

The calibration set must contain questions answerable from the assetized answer
bank. Therefore this script excludes synthetic llm_direct supplements and
mentor_needed cases by default, and uses realQA partial cases only.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATASET_JSON = ROOT / "eval" / "agent2_balanced_with_direct_supplement.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_conformal_retrieval_calibration.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def quantile_cutoff(values: list[float], alpha: float) -> float:
    if not values:
        raise ValueError("No calibration values.")
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
    args = parser.parse_args()

    dataset = load_json(DATASET_JSON)
    cases = dataset.get("cases", [])

    calibration_cases = [
        case for case in cases
        if case.get("case_id", "").startswith("realqa_")
        and case.get("gold", {}).get("verdict") == "partial_with_mentor_suggest"
        and isinstance(case.get("source_answer_similarity"), (int, float))
    ]
    calibration_values = [case["source_answer_similarity"] for case in calibration_cases]

    all_answerable_values = [
        case["source_answer_similarity"] for case in cases
        if case.get("gold", {}).get("verdict") in {"partial_with_mentor_suggest", "llm_direct"}
        and isinstance(case.get("source_answer_similarity"), (int, float))
    ]
    realqa_mentor_values = [
        case["source_answer_similarity"] for case in cases
        if case.get("case_id", "").startswith("realqa_")
        and case.get("gold", {}).get("verdict") == "mentor_needed"
        and isinstance(case.get("source_answer_similarity"), (int, float))
    ]
    direct_supp_values = [
        case["source_answer_similarity"] for case in cases
        if case.get("case_id", "").startswith("direct_supp_")
        and isinstance(case.get("source_answer_similarity"), (int, float))
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
        "description": "CONFLARE-style conformal retrieval calibration for Agent2.",
        "method": "Use source_answer_similarity of realQA partial cases as the calibration distribution. The cutoff is the lower alpha quantile, so retrieving chunks above the cutoff gives approximately 1-alpha calibration coverage.",
        "dataset": str(DATASET_JSON.relative_to(ROOT)),
        "calibration_filter": {
            "case_id_prefix": "realqa_",
            "gold_verdict": "partial_with_mentor_suggest",
            "reason": "These are answerable from the asset answer bank. Synthetic llm_direct and mentor_needed cases violate the retrieval-calibration assumption.",
        },
        "distributions": {
            "calibration_realqa_partial": describe(calibration_values),
            "all_answerable_including_direct_supplement": describe(all_answerable_values),
            "realqa_mentor_needed": describe(realqa_mentor_values),
            "direct_supplement": describe(direct_supp_values),
        },
        "alpha_results": alpha_results,
        "calibration_case_ids": [case["case_id"] for case in calibration_cases],
    }
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
