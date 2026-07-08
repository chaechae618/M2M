"""
Simulate a code-based usable fallback for Agent2 without calling the OpenAI API.

The simulation starts from eval/agent2_baseline_results.json and changes only
cases that originally fell back with no_usable_answers. This lets us estimate
whether a narrow search_first fallback is worth implementing in Agent2.

Output:
  eval/agent2_usable_fallback_simulation.json
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASELINE_JSON = ROOT / "eval" / "agent2_baseline_results.json"
DATASET_JSON = ROOT / "eval" / "agent2_balanced_with_direct_supplement.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_usable_fallback_simulation.json"

LABELS = ["llm_direct", "partial_with_mentor_suggest", "mentor_needed"]

BLOCK_KEYWORDS = [
    "가능할까요",
    "괜찮을까요",
    "제 스펙",
    "제 상황",
    "저에게 맞",
    "선택해야",
    "합격 가능",
    "이직 가능",
    "첨부",
    "자소서 봐",
    "포트폴리오 봐",
    "피드백",
    "불합격",
    "탈락",
]

GENERAL_HINTS = [
    "무엇인가요",
    "어떤 역량",
    "어떤 경험",
    "준비",
    "방법",
    "필요한 기술",
    "차이점",
    "중점",
    "구성",
    "요소",
    "직무",
    "역량",
]

CONSERVATIVE_SCORE = 0.585


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def is_general_question(text: str) -> bool:
    if any(keyword in text for keyword in BLOCK_KEYWORDS):
        return False
    return any(keyword in text for keyword in GENERAL_HINTS)


def confusion_matrix(results: list[dict]) -> dict:
    matrix = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    for item in results:
        matrix[item["gold_verdict"]][item["predicted_verdict"]] += 1
    return matrix


def per_label(results: list[dict]) -> dict:
    out = {}
    for label in LABELS:
        tp = sum(1 for r in results if r["gold_verdict"] == label and r["predicted_verdict"] == label)
        fp = sum(1 for r in results if r["gold_verdict"] != label and r["predicted_verdict"] == label)
        fn = sum(1 for r in results if r["gold_verdict"] == label and r["predicted_verdict"] != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    return out


def summarize(results: list[dict]) -> dict:
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    wrong_direct = [
        r for r in results
        if r["predicted_verdict"] == "llm_direct" and r["gold_verdict"] != "llm_direct"
    ]
    mentor_needed_missed = [
        r for r in results
        if r["gold_verdict"] == "mentor_needed" and r["predicted_verdict"] != "mentor_needed"
    ]
    return {
        "case_count": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "gold_counts": dict(Counter(r["gold_verdict"] for r in results)),
        "predicted_counts": dict(Counter(r["predicted_verdict"] for r in results)),
        "wrong_direct_answer_count": len(wrong_direct),
        "wrong_direct_answer_case_ids": [r["case_id"] for r in wrong_direct],
        "mentor_needed_missed_count": len(mentor_needed_missed),
        "mentor_needed_missed_case_ids": [r["case_id"] for r in mentor_needed_missed],
        "confusion_matrix": confusion_matrix(results),
        "per_label": per_label(results),
    }


def fallback_allowed(result: dict, case: dict, top1_threshold: float) -> tuple[bool, str]:
    if result.get("strategy") != "search_first":
        return False, "not_search_first"
    if result.get("fallback_type") != "no_usable_answers":
        return False, "not_no_usable"
    if result.get("predicted_verdict") != "mentor_needed":
        return False, "not_mentor_needed"
    if case.get("features", {}).get("top1_similarity", 0.0) < top1_threshold:
        return False, "low_similarity"
    flags = case.get("gold", {}).get("hard_case_flags", {}) or {}
    if flags.get("requires_artifact_review"):
        return False, "artifact_review"
    if not is_general_question(case.get("query", "") or case.get("title", "")):
        return False, "not_general_question"
    return True, "allowed"


def simulate_variant(
    baseline_results: list[dict],
    cases_by_id: dict[str, dict],
    top1_threshold: float,
    direct_threshold: float = 0.65,
    mid_threshold: float = 0.45,
) -> dict:
    simulated = []
    reasons = Counter()
    changed = []

    for result in baseline_results:
        item = dict(result)
        case = cases_by_id[item["case_id"]]
        allowed, reason = fallback_allowed(item, case, top1_threshold)
        reasons[reason] += 1

        if allowed:
            score = CONSERVATIVE_SCORE
            if score >= direct_threshold:
                pred = "llm_direct"
            elif score >= mid_threshold:
                pred = "partial_with_mentor_suggest"
            else:
                pred = "mentor_needed"
            item["predicted_verdict"] = pred
            item["avg_score"] = score
            item["fallback_type"] = None
            item["fallback_reason"] = None
            item["usable_fallback_applied"] = True
            item["usable_fallback_reason"] = {
                "top1_threshold": top1_threshold,
                "top1_similarity": case.get("features", {}).get("top1_similarity"),
                "score": score,
            }
            changed.append(item["case_id"])
        else:
            item["usable_fallback_applied"] = False
            item["usable_fallback_block_reason"] = reason

        item["correct"] = item["gold_verdict"] == item["predicted_verdict"]
        simulated.append(item)

    return {
        "config": {
            "top1_threshold": top1_threshold,
            "direct_threshold": direct_threshold,
            "mid_threshold": mid_threshold,
            "conservative_score": CONSERVATIVE_SCORE,
        },
        "changed_count": len(changed),
        "changed_case_ids": changed,
        "block_reasons": dict(reasons),
        "summary": summarize(simulated),
        "results": simulated,
    }


def main() -> None:
    baseline = load_json(BASELINE_JSON)
    dataset = load_json(DATASET_JSON)
    baseline_results = baseline["results"]
    cases_by_id = {case["case_id"]: case for case in dataset["cases"]}

    variants = {}
    for top1_threshold in [0.50, 0.48, 0.45]:
        key = f"fallback_top1_{str(top1_threshold).replace('.', '')}"
        variants[key] = simulate_variant(
            baseline_results,
            cases_by_id,
            top1_threshold=top1_threshold,
        )

    output = {
        "description": "Offline simulation of search_first no_usable_answers fallback.",
        "baseline_summary": baseline["summary"],
        "variants": variants,
    }
    write_json(OUTPUT_JSON, output)
    print(json.dumps({
        "output": str(OUTPUT_JSON),
        "baseline": baseline["summary"],
        "variants": {
            key: {
                "changed_count": value["changed_count"],
                "summary": value["summary"],
            }
            for key, value in variants.items()
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
