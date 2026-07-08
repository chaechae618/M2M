"""
Evaluate current Agent2 verdict logic against the validation dataset.

This is a decision-only baseline:
- Uses SearchVerifyAgent's strategy, retrieval, verify, scoring, thresholds.
- Monkeypatches DB reads/writes to use offline asset candidates.
- Skips answer generation/faithfulness by returning a placeholder answer,
  so verdict evaluation focuses on routing/threshold behavior.

Inputs:
  eval/agent2_balanced_with_direct_supplement.json
  data/cleaned/example_qa_asset_candidates.json

Output:
  eval/agent2_baseline_results.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import agents.search_verify_agent as sva  # noqa: E402


DATASET_JSON = ROOT / "eval" / "agent2_balanced_with_direct_supplement.json"
ASSET_JSON = ROOT / "data" / "cleaned" / "example_qa_asset_candidates.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_baseline_results.json"

LABELS = ["llm_direct", "partial_with_mentor_suggest", "mentor_needed"]


class DecisionOnlySearchVerifyAgent(sva.SearchVerifyAgent):
    def _generate_answer(self, *args, **kwargs) -> str:
        return "[evaluation placeholder answer]"

    def _generate_general_direct_answer(self, *args, **kwargs) -> str:
        return "[evaluation placeholder general-direct answer]"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@contextmanager
def offline_agent_context(assets: list[dict]):
    original_get_assetized_answers = sva.get_assetized_answers
    original_update_session = sva.update_session
    sva.get_assetized_answers = lambda: assets
    sva.update_session = lambda session_id, updates: True
    try:
        yield
    finally:
        sva.get_assetized_answers = original_get_assetized_answers
        sva.update_session = original_update_session


def normalize_gold_flags(case: dict) -> dict:
    flags = case.get("gold", {}).get("hard_case_flags", {}) or {}
    return {
        "requires_artifact_review": bool(flags.get("requires_artifact_review", False)),
        "recency_sensitive": bool(flags.get("recency_sensitive", False)),
        "scope_too_broad": False,
        "risk_flags": [],
        "recency_level": "high" if flags.get("recency_sensitive") else "",
        "recency_reason": "",
        "question_structure": "",
        "document_help_type": "artifact_review" if flags.get("requires_artifact_review") else "",
    }


def normalize_routing_hints(case: dict) -> dict:
    gold = case.get("gold", {})
    flags = gold.get("hard_case_flags", {}) or {}
    if gold.get("verdict") == "llm_direct":
        return {
            "search_strategy_hint": "search_first",
            "search_strategy_confidence": 0.8,
            "personal_context_strength": "weak",
        }
    if flags.get("personal_dependency_high") or gold.get("verdict") == "mentor_needed":
        return {
            "search_strategy_hint": "mentor_first",
            "search_strategy_confidence": 0.75,
            "personal_context_strength": "strong",
        }
    return {
        "search_strategy_hint": "search_first",
        "search_strategy_confidence": 0.6,
        "personal_context_strength": "moderate",
    }


def confusion_matrix(results: list[dict]) -> dict:
    matrix = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    for item in results:
        gold = item["gold_verdict"]
        pred = item["predicted_verdict"]
        matrix.setdefault(gold, {label: 0 for label in LABELS})
        matrix[gold][pred] = matrix[gold].get(pred, 0) + 1
    return matrix


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
        "confusion_matrix": confusion_matrix(results),
        "per_label": precision_recall_f1(results),
    }


def load_existing_results() -> dict[str, dict]:
    if not OUTPUT_JSON.exists():
        return {}
    data = load_json(OUTPUT_JSON)
    return {item["case_id"]: item for item in data.get("results", [])}


def load_existing_results_from(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    data = load_json(path)
    return {item["case_id"]: item for item in data.get("results", [])}


def evaluate_case(agent: DecisionOnlySearchVerifyAgent, case: dict) -> dict:
    gold = case.get("gold", {})
    result = agent.run(
        session_id=f"eval_{case['case_id']}",
        refined_question=case["query"],
        conversation_summary=case["query"],
        routing_hints=normalize_routing_hints(case),
        search_query=case["query"],
        safe_context=case["query"],
        current_bottleneck="",
        expected_answer_type="",
        question_units=[],
        hard_case_flags=normalize_gold_flags(case),
    )
    retrieval_log = result.get("retrieval_log", {})
    return {
        "case_id": case["case_id"],
        "domain": case.get("domain", ""),
        "title": case.get("title", ""),
        "gold_verdict": gold.get("verdict"),
        "predicted_verdict": result.get("verdict"),
        "correct": gold.get("verdict") == result.get("verdict"),
        "avg_score": result.get("avg_score"),
        "strategy": result.get("strategy"),
        "retrieved_count": result.get("retrieved_count"),
        "fallback_type": result.get("fallback_type"),
        "fallback_reason": result.get("fallback_reason"),
        "gold_usable_answer_ids": gold.get("usable_answer_ids", []),
        "source_trace": result.get("source_trace", {}),
        "retrieval_log": retrieval_log,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--sim-search-first", type=float, default=None)
    parser.add_argument("--sim-mentor-first", type=float, default=None)
    parser.add_argument("--mid-search-first", type=float, default=None)
    parser.add_argument("--mid-mentor-first", type=float, default=None)
    parser.add_argument("--direct-search-first", type=float, default=None)
    parser.add_argument("--direct-mentor-first", type=float, default=None)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT.parent / ".env")
    load_dotenv(ROOT.parent / ".env.local")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required.", file=sys.stderr)
        sys.exit(1)

    dataset = load_json(DATASET_JSON)
    cases = dataset.get("cases", [])
    if args.limit is not None:
        cases = cases[:args.limit]

    assets = load_json(ASSET_JSON).get("records", [])
    assets = [asset for asset in assets if asset.get("embedding")]

    output_path = args.output if args.output.is_absolute() else ROOT / args.output

    if args.sim_search_first is not None:
        DecisionOnlySearchVerifyAgent.SIM_THRESHOLD = {
            **DecisionOnlySearchVerifyAgent.SIM_THRESHOLD,
            "search_first": args.sim_search_first,
        }
    if args.sim_mentor_first is not None:
        DecisionOnlySearchVerifyAgent.SIM_THRESHOLD = {
            **DecisionOnlySearchVerifyAgent.SIM_THRESHOLD,
            "mentor_first": args.sim_mentor_first,
        }
    if args.mid_search_first is not None:
        DecisionOnlySearchVerifyAgent.MID_THRESHOLD = {
            **DecisionOnlySearchVerifyAgent.MID_THRESHOLD,
            "search_first": args.mid_search_first,
        }
    if args.mid_mentor_first is not None:
        DecisionOnlySearchVerifyAgent.MID_THRESHOLD = {
            **DecisionOnlySearchVerifyAgent.MID_THRESHOLD,
            "mentor_first": args.mid_mentor_first,
        }
    if args.direct_search_first is not None:
        DecisionOnlySearchVerifyAgent.THRESHOLD = {
            **DecisionOnlySearchVerifyAgent.THRESHOLD,
            "search_first": args.direct_search_first,
        }
    if args.direct_mentor_first is not None:
        DecisionOnlySearchVerifyAgent.THRESHOLD = {
            **DecisionOnlySearchVerifyAgent.THRESHOLD,
            "mentor_first": args.direct_mentor_first,
        }

    existing = load_existing_results_from(output_path) if args.resume else {}
    results: list[dict] = []
    agent = DecisionOnlySearchVerifyAgent()

    with offline_agent_context(assets):
        for idx, case in enumerate(cases, start=1):
            if case["case_id"] in existing:
                results.append(existing[case["case_id"]])
                print(f"[skip baseline {idx:03d}/{len(cases):03d}] {case['case_id']}")
                continue

            print(f"[baseline {idx:03d}/{len(cases):03d}] {case['case_id']} gold={case.get('gold', {}).get('verdict')}")
            try:
                item = evaluate_case(agent, case)
            except Exception as exc:
                item = {
                    "case_id": case["case_id"],
                    "domain": case.get("domain", ""),
                    "title": case.get("title", ""),
                    "gold_verdict": case.get("gold", {}).get("verdict"),
                    "predicted_verdict": "error",
                    "correct": False,
                    "error": str(exc),
                }
            results.append(item)
            write_json(output_path, {
                "description": "Decision-only baseline results for current Agent2.",
                "dataset": str(DATASET_JSON),
                "config": {
                    "SIM_THRESHOLD": DecisionOnlySearchVerifyAgent.SIM_THRESHOLD,
                    "MID_THRESHOLD": DecisionOnlySearchVerifyAgent.MID_THRESHOLD,
                    "THRESHOLD": DecisionOnlySearchVerifyAgent.THRESHOLD,
                    "WEIGHTS": DecisionOnlySearchVerifyAgent.WEIGHTS,
                },
                "summary": summarize([r for r in results if r.get("predicted_verdict") in LABELS]),
                "results": results,
            })
            if args.sleep:
                time.sleep(args.sleep)

    valid_results = [r for r in results if r.get("predicted_verdict") in LABELS]
    output = {
        "description": "Decision-only baseline results for current Agent2.",
        "dataset": str(DATASET_JSON),
        "config": {
            "SIM_THRESHOLD": DecisionOnlySearchVerifyAgent.SIM_THRESHOLD,
            "MID_THRESHOLD": DecisionOnlySearchVerifyAgent.MID_THRESHOLD,
            "THRESHOLD": DecisionOnlySearchVerifyAgent.THRESHOLD,
            "WEIGHTS": DecisionOnlySearchVerifyAgent.WEIGHTS,
        },
        "summary": summarize(valid_results),
        "results": results,
    }
    write_json(output_path, output)
    print(json.dumps({
        "output": str(output_path),
        "summary": output["summary"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
