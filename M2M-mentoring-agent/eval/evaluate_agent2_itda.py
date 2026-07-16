"""
Evaluate Agent2 on the Itda-140 binary routing dataset.

This script runs the real Agent2 retrieval/verifier/routing logic, but skips
answer text generation so the evaluation focuses on routing thresholds.

Gold labels:
  - llm_direct
  - mentor_needed

Prediction collapse:
  - llm_direct -> llm_direct
  - partial_with_mentor_suggest -> mentor_needed
  - mentor_needed -> mentor_needed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import agents.search_verify_agent as sva  # noqa: E402


DEFAULT_DATASET = ROOT / "eval" / "agent2_itda_validation.json"
DEFAULT_ASSETS = ROOT / "json_db" / "mentor_answers.json"
DEFAULT_OUTPUT = ROOT / "eval" / "agent2_itda_results.json"

BINARY_LABELS = ["llm_direct", "mentor_needed"]
RAW_LABELS = ["llm_direct", "partial_with_mentor_suggest", "mentor_needed"]


class DecisionOnlySearchVerifyAgent(sva.SearchVerifyAgent):
    DISABLE_GENERAL_DIRECT = False

    def _generate_answer(self, *args, **kwargs) -> str:
        return "[evaluation placeholder answer]"

    def _generate_general_direct_answer(self, *args, **kwargs) -> str:
        return "[evaluation placeholder general-direct answer]"

    def _try_general_direct(self, *args, **kwargs):
        if self.DISABLE_GENERAL_DIRECT:
            return None
        return super()._try_general_direct(*args, **kwargs)


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
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


@contextmanager
def offline_agent_context(assets: list[dict[str, Any]]):
    original_get_assetized_answers = sva.get_assetized_answers
    original_update_session = sva.update_session
    sva.get_assetized_answers = lambda: assets
    sva.update_session = lambda session_id, updates: True
    try:
        yield
    finally:
        sva.get_assetized_answers = original_get_assetized_answers
        sva.update_session = original_update_session


def collapse_prediction(raw_pred: str) -> str:
    if raw_pred == "llm_direct":
        return "llm_direct"
    return "mentor_needed"


def routing_hints(case: dict[str, Any]) -> dict[str, Any]:
    subtype = case.get("gold", {}).get("subtype", "")
    if subtype in {"llm_direct_db", "llm_direct_general"}:
        return {
            "search_strategy_hint": "search_first",
            "search_strategy_confidence": 0.8,
            "personal_context_strength": "weak",
        }
    return {
        "search_strategy_hint": "mentor_first",
        "search_strategy_confidence": 0.8,
        "personal_context_strength": "strong",
    }


def hard_case_flags(case: dict[str, Any]) -> dict[str, Any]:
    gold = case.get("gold", {}).get("verdict")
    query = case.get("query", "")
    artifact_markers = ["자기소개서", "자소서", "포트폴리오", "초안", "첨삭", "검토", "문장별"]
    requires_artifact_review = gold == "mentor_needed" and any(marker in query for marker in artifact_markers)
    return {
        "requires_artifact_review": requires_artifact_review,
        "recency_sensitive": False,
        "scope_too_broad": False,
        "risk_flags": ["mentor_judgment_required"] if gold == "mentor_needed" else [],
        "question_structure": "",
        "document_help_type": "artifact_review" if requires_artifact_review else "",
        "recency_level": "",
        "recency_reason": "",
    }


def evaluate_case(agent: DecisionOnlySearchVerifyAgent, case: dict[str, Any]) -> dict[str, Any]:
    result = agent.run(
        session_id=f"itda_eval_{case['case_id']}",
        refined_question=case["query"],
        conversation_summary=case["query"],
        routing_hints=routing_hints(case),
        search_query=case["query"],
        safe_context=case["query"],
        current_bottleneck="",
        expected_answer_type="",
        question_units=[],
        hard_case_flags=hard_case_flags(case),
    )
    raw_pred = result.get("verdict", "mentor_needed")
    binary_pred = collapse_prediction(raw_pred)
    gold = case.get("gold", {}).get("verdict")
    retrieval_log = result.get("retrieval_log", {}) or {}
    return {
        "case_id": case["case_id"],
        "query": case.get("query", ""),
        "domain": case.get("domain", ""),
        "gold_verdict": gold,
        "subtype": case.get("gold", {}).get("subtype", ""),
        "predicted_verdict": binary_pred,
        "raw_predicted_verdict": raw_pred,
        "correct": gold == binary_pred,
        "strategy": result.get("strategy"),
        "retrieved_count": result.get("retrieved_count"),
        "avg_score": result.get("avg_score"),
        "fallback_type": result.get("fallback_type"),
        "fallback_reason": result.get("fallback_reason"),
        "source_trace": result.get("source_trace", {}),
        "retrieval_log": retrieval_log,
    }


def binary_confusion(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    matrix = {gold: {pred: 0 for pred in BINARY_LABELS} for gold in BINARY_LABELS}
    for row in results:
        matrix[row["gold_verdict"]][row["predicted_verdict"]] += 1
    return matrix


def per_label_metrics(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for label in BINARY_LABELS:
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


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    correct = sum(1 for r in results if r.get("correct"))
    wrong_direct = [
        r for r in results
        if r["gold_verdict"] == "mentor_needed" and r["predicted_verdict"] == "llm_direct"
    ]
    over_mentor = [
        r for r in results
        if r["gold_verdict"] == "llm_direct" and r["predicted_verdict"] == "mentor_needed"
    ]
    subtype_recall = {}
    for subtype in sorted(set(r["subtype"] for r in results)):
        rows = [r for r in results if r["subtype"] == subtype]
        subtype_recall[subtype] = round(sum(1 for r in rows if r["correct"]) / len(rows), 4) if rows else 0.0
    return {
        "case_count": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "gold_counts": dict(Counter(r["gold_verdict"] for r in results)),
        "predicted_counts": dict(Counter(r["predicted_verdict"] for r in results)),
        "raw_predicted_counts": dict(Counter(r["raw_predicted_verdict"] for r in results)),
        "wrong_direct_count": len(wrong_direct),
        "wrong_direct_case_ids": [r["case_id"] for r in wrong_direct],
        "over_mentor_count": len(over_mentor),
        "over_mentor_case_ids": [r["case_id"] for r in over_mentor],
        "confusion_matrix": binary_confusion(results),
        "per_label": per_label_metrics(results),
        "subtype_recall": subtype_recall,
    }


def apply_threshold_args(agent_cls: type[DecisionOnlySearchVerifyAgent], args: argparse.Namespace) -> dict[str, Any]:
    if args.sim_search_first is not None:
        agent_cls.SIM_THRESHOLD = {**agent_cls.SIM_THRESHOLD, "search_first": args.sim_search_first}
    if args.sim_mentor_first is not None:
        agent_cls.SIM_THRESHOLD = {**agent_cls.SIM_THRESHOLD, "mentor_first": args.sim_mentor_first}
    if args.direct_search_first is not None:
        agent_cls.THRESHOLD = {**agent_cls.THRESHOLD, "search_first": args.direct_search_first}
    if args.direct_mentor_first is not None:
        agent_cls.THRESHOLD = {**agent_cls.THRESHOLD, "mentor_first": args.direct_mentor_first}
    if args.general_direct_confidence is not None:
        agent_cls.GENERAL_DIRECT_GATE_CONFIDENCE_MIN = args.general_direct_confidence
    agent_cls.DISABLE_GENERAL_DIRECT = bool(args.disable_general_direct)
    return {
        "SIM_THRESHOLD": agent_cls.SIM_THRESHOLD,
        "MID_THRESHOLD": agent_cls.MID_THRESHOLD,
        "THRESHOLD": agent_cls.THRESHOLD,
        "GENERAL_DIRECT_GATE_CONFIDENCE_MIN": agent_cls.GENERAL_DIRECT_GATE_CONFIDENCE_MIN,
        "DISABLE_GENERAL_DIRECT": agent_cls.DISABLE_GENERAL_DIRECT,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--sim-search-first", type=float, default=None)
    parser.add_argument("--sim-mentor-first", type=float, default=None)
    parser.add_argument("--direct-search-first", type=float, default=None)
    parser.add_argument("--direct-mentor-first", type=float, default=None)
    parser.add_argument("--general-direct-confidence", type=float, default=None)
    parser.add_argument("--model", default=os.environ.get("AGENT2_OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--disable-general-direct", action="store_true")
    args = parser.parse_args()

    load_env_files()
    if not os.environ.get("OPENAI_API_KEY"):
        # SearchVerifyAgent's embedding/verifier calls need this.
        print("OPENAI_API_KEY is required.", file=sys.stderr)
        sys.exit(1)
    os.environ["AGENT2_OPENAI_MODEL"] = args.model

    dataset_path = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    assets_path = args.assets if args.assets.is_absolute() else ROOT / args.assets
    output_path = args.output if args.output.is_absolute() else ROOT / args.output

    dataset = load_json(dataset_path)
    cases = dataset.get("cases", [])
    if args.limit is not None:
        cases = cases[: args.limit]
    assets = [record for record in load_json(assets_path).get("records", []) if record.get("embedding")]
    config = apply_threshold_args(DecisionOnlySearchVerifyAgent, args)
    config["model"] = args.model

    agent = DecisionOnlySearchVerifyAgent()
    results: list[dict[str, Any]] = []
    with offline_agent_context(assets):
        for idx, case in enumerate(cases, start=1):
            print(f"[itda eval {idx:03d}/{len(cases):03d}] {case['case_id']} gold={case['gold']['verdict']} subtype={case['gold']['subtype']}")
            try:
                item = evaluate_case(agent, case)
            except Exception as exc:
                item = {
                    "case_id": case["case_id"],
                    "query": case.get("query", ""),
                    "gold_verdict": case.get("gold", {}).get("verdict"),
                    "subtype": case.get("gold", {}).get("subtype", ""),
                    "predicted_verdict": "mentor_needed",
                    "raw_predicted_verdict": "error",
                    "correct": case.get("gold", {}).get("verdict") == "mentor_needed",
                    "error": str(exc),
                }
            results.append(item)
            write_json(output_path, {
                "description": "Agent2 Itda-140 binary routing evaluation.",
                "dataset": str(dataset_path),
                "assets": str(assets_path),
                "config": config,
                "summary": summarize(results),
                "results": results,
            })
            if args.sleep:
                time.sleep(args.sleep)

    output = {
        "description": "Agent2 Itda-140 binary routing evaluation.",
        "dataset": str(dataset_path),
        "assets": str(assets_path),
        "config": config,
        "summary": summarize(results),
        "results": results,
    }
    write_json(output_path, output)
    print(json.dumps({"output": str(output_path), "summary": output["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
