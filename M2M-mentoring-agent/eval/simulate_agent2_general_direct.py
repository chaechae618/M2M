"""
Offline simulation for a general-knowledge direct-answer route.

This does not call the model. It replays the latest Agent2 evaluation output and
simulates whether clearly general search_first questions could become
llm_direct even when asset retrieval is empty or verifier produced only a
conservative partial route.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "eval" / "agent2_usable_fallback_applied_results.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_general_direct_simulation.json"

LABELS = ["llm_direct", "partial_with_mentor_suggest", "mentor_needed"]

GENERAL_INFO_HINTS = [
    "무엇", "뭐", "어떤", "어떻게", "방법", "준비", "스킬", "역량",
    "직무", "업무", "역할", "면접", "포트폴리오", "자소서", "로드맵",
    "차이", "차이점", "종류", "과정", "현업", "평균", "트렌드", "필요",
    "고려", "요소", "개발", "학습", "중요",
]

PERSONAL_JUDGMENT_BLOCKERS = [
    "제 상황", "내 상황", "저한테", "나한테", "저에게", "나에게",
    "가능할까요", "맞을까요", "괜찮을까요", "될까요", "합격",
    "스펙", "학점", "학년", "전공인데", "가족", "경제", "지역", "지방",
    "포트폴리오 봐", "첨삭", "이력서 봐", "자소서 봐",
]

DIRECT_INTENT_HINTS = [
    "무엇인가요", "뭔가요", "어떤", "어떻게", "방법", "차이점",
    "필요한 역량", "중요", "고려", "요소", "학습", "개발",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def is_general_info_question(text: str) -> bool:
    c = compact(text)
    if not c:
        return False
    if any(token in c for token in PERSONAL_JUDGMENT_BLOCKERS):
        return False
    return any(token in c for token in GENERAL_INFO_HINTS)


def has_direct_intent(text: str) -> bool:
    c = compact(text)
    return any(token in c for token in DIRECT_INTENT_HINTS)


def hard_flags(item: dict) -> dict:
    return item.get("retrieval_log", {}).get("hard_case_flags", {}) or {}


def is_safe_general_direct_candidate(item: dict) -> bool:
    flags = hard_flags(item)
    if flags.get("requires_artifact_review"):
        return False
    if flags.get("risk_flags"):
        return False
    question = item.get("title") or item.get("retrieval_log", {}).get("session_id", "")
    return is_general_info_question(question) and has_direct_intent(question)


def summarize(results: list[dict]) -> dict:
    total = len(results)
    correct = sum(1 for r in results if r["gold_verdict"] == r["predicted_verdict"])
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
        "per_label": precision_recall_f1(results),
    }


def precision_recall_f1(results: list[dict]) -> dict:
    out: dict[str, dict] = {}
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


def apply_variant(results: list[dict], variant: str) -> tuple[list[dict], list[str]]:
    changed: list[str] = []
    updated = deepcopy(results)
    for item in updated:
        if item.get("strategy") != "search_first":
            continue
        if not is_safe_general_direct_candidate(item):
            continue

        promote = False
        if variant in {"no_similar_only", "no_similar_plus_low_sim_partial"}:
            promote = item.get("fallback_type") == "no_similar_answers"

        if variant == "no_similar_plus_low_sim_partial":
            fallback = item.get("retrieval_log", {}).get("usable_fallback") or {}
            top1 = float(fallback.get("top1_similarity") or 0.0)
            if item.get("predicted_verdict") == "partial_with_mentor_suggest" and 0.0 < top1 <= 0.65:
                promote = True

        if promote:
            item["predicted_verdict"] = "llm_direct"
            item["fallback_type"] = None
            item["fallback_reason"] = None
            item.setdefault("retrieval_log", {})["general_direct_simulated"] = {
                "variant": variant,
                "reason": "safe search_first general-info question promoted to llm_direct",
            }
            changed.append(item["case_id"])

    return updated, changed


def main() -> None:
    baseline = load_json(INPUT_JSON)
    results = baseline["results"]
    variants = {}
    for variant in ["no_similar_only", "no_similar_plus_low_sim_partial"]:
        updated, changed = apply_variant(results, variant)
        variants[variant] = {
            "changed_count": len(changed),
            "changed_case_ids": changed,
            "summary": summarize(updated),
        }

    payload = {
        "description": "Offline simulation of a general-knowledge direct-answer route.",
        "input": str(INPUT_JSON.relative_to(ROOT)),
        "baseline_summary": baseline["summary"],
        "variants": variants,
    }
    write_json(OUTPUT_JSON, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
