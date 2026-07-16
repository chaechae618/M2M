"""
Cached grid search for Agent2 Itda thresholds.

Requires a retrieval cache from build_agent2_itda_retrieval_cache.py.

What is cached:
  - query embeddings and retrieval similarities in agent2_itda_retrieval_cache.json
  - LLM verifier/gate decisions in agent2_itda_llm_decision_cache.json

This avoids repeating query embedding calls for every threshold combination.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import agents.search_verify_agent as sva  # noqa: E402
from eval.evaluate_agent2_itda import hard_case_flags, routing_hints  # noqa: E402


RETRIEVAL_CACHE = ROOT / "eval" / "agent2_itda_retrieval_cache.json"
LLM_CACHE = ROOT / "eval" / "agent2_itda_llm_decision_cache.json"
ASSETS_JSON = ROOT / "json_db" / "mentor_answers.json"
SUMMARY_JSON = ROOT / "eval" / "agent2_itda_cached_grid_summary.json"
REPORT_HTML = ROOT / "eval" / "agent2_itda_cached_grid_report.html"

BINARY_LABELS = ["llm_direct", "mentor_needed"]


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
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


class DecisionOnlyAgent(sva.SearchVerifyAgent):
    def _generate_answer(self, *args, **kwargs) -> str:
        return "[evaluation placeholder answer]"

    def _generate_general_direct_answer(self, *args, **kwargs) -> str:
        return "[evaluation placeholder general-direct answer]"


def cache_key(parts: list[Any]) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def get_verify(
    agent: DecisionOnlyAgent,
    llm_cache: dict[str, Any],
    case: dict[str, Any],
    retrieved: list[dict[str, Any]],
    model: str,
) -> dict[str, Any]:
    answer_ids = [item["answer_id"] for item in retrieved]
    key = cache_key(["verify", model, case["case_id"], answer_ids])
    if key not in llm_cache["verify"]:
        flags = hard_case_flags(case)
        risk_flags = flags.get("risk_flags", [])
        llm_cache["verify"][key] = agent._verify(
            case["query"],
            case["query"],
            retrieved,
            current_bottleneck="",
            expected_answer_type="",
            question_units=[],
            risk_flags=risk_flags,
        )
    return llm_cache["verify"][key]


def get_gate(
    agent: DecisionOnlyAgent,
    llm_cache: dict[str, Any],
    case: dict[str, Any],
    general_confidence: float,
    model: str,
) -> dict[str, Any]:
    key = cache_key(["general_gate", model, case["case_id"], round(general_confidence, 4)])
    if key not in llm_cache["general_gate"]:
        original = agent.GENERAL_DIRECT_GATE_CONFIDENCE_MIN
        agent.GENERAL_DIRECT_GATE_CONFIDENCE_MIN = general_confidence
        llm_cache["general_gate"][key] = agent._judge_general_direct(
            question=case["query"],
            context=case["query"],
            hard_case_flags=hard_case_flags(case),
        )
        agent.GENERAL_DIRECT_GATE_CONFIDENCE_MIN = original
    return llm_cache["general_gate"][key]


def collapse(raw_pred: str) -> str:
    return "llm_direct" if raw_pred == "llm_direct" else "mentor_needed"


def evaluate_case(
    agent: DecisionOnlyAgent,
    llm_cache: dict[str, Any],
    case: dict[str, Any],
    assets_by_id: dict[str, dict[str, Any]],
    sim_threshold: float,
    direct_threshold: float,
    general_confidence: float,
    disable_general_direct: bool,
    model: str,
) -> dict[str, Any]:
    hints = routing_hints(case)
    flags = hard_case_flags(case)
    strategy = hints.get("search_strategy_hint", "mentor_first")
    if strategy not in ("search_first", "mentor_first"):
        strategy = "mentor_first"

    risk_flags = flags.get("risk_flags", []) or []
    threshold_boost = 0.05 if risk_flags else 0.0
    if flags.get("requires_artifact_review"):
        raw_pred = "mentor_needed"
        return result_row(case, raw_pred, strategy, 0, 0.0, "requires_artifact_review")

    top5 = case.get("top", [])[:5]
    retrieved = []
    for row in top5:
        if float(row["similarity"]) >= sim_threshold:
            asset = dict(assets_by_id[row["answer_id"]])
            asset["_similarity_score"] = float(row["similarity"])
            retrieved.append(asset)

    if not retrieved:
        if not disable_general_direct and agent._is_general_direct_gate_candidate(
            strategy=strategy,
            question=case["query"],
            hard_case_flags=flags,
        ):
            gate = get_gate(agent, llm_cache, case, general_confidence, model)
            if gate.get("direct_general_allowed"):
                return result_row(case, "llm_direct", strategy, 0, 1.0, "general_direct_no_similar")
        return result_row(case, "mentor_needed", strategy, 0, 0.0, "no_similar_answers")

    verify = get_verify(agent, llm_cache, case, retrieved, model)
    scores = verify.get("scores", {}) or {}
    usable_ids = sva.normalize_ids(verify.get("usable_answer_ids", []), len(retrieved))
    if not usable_ids:
        return result_row(case, "mentor_needed", strategy, len(retrieved), 0.0, "no_usable_answers")

    recency_avg = sum(sva._calc_recency(item) for item in retrieved) / len(retrieved)
    weights = {k: v for k, v in agent.WEIGHTS[strategy].items()}
    avg_score = (
        sva.safe_float(scores.get("relevance", 0.0)) * weights["relevance"]
        + sva.safe_float(scores.get("evidence_sufficiency", 0.0)) * weights["evidence_sufficiency"]
        + sva.safe_float(scores.get("situation_fit", 0.0)) * weights["situation_fit"]
        + recency_avg * weights["recency"]
    )
    privacy_safe = sva.safe_bool(scores.get("privacy_safe"), default=False)
    threshold = direct_threshold + threshold_boost

    if avg_score >= threshold and privacy_safe:
        raw_pred = "llm_direct"
    else:
        raw_pred = "mentor_needed"
    return result_row(case, raw_pred, strategy, len(retrieved), avg_score, None)


def result_row(
    case: dict[str, Any],
    raw_pred: str,
    strategy: str,
    retrieved_count: int,
    avg_score: float,
    fallback_type: str | None,
) -> dict[str, Any]:
    pred = collapse(raw_pred)
    gold = case["gold"]["verdict"]
    return {
        "case_id": case["case_id"],
        "gold_verdict": gold,
        "subtype": case["gold"].get("subtype", ""),
        "raw_predicted_verdict": raw_pred,
        "predicted_verdict": pred,
        "correct": gold == pred,
        "strategy": strategy,
        "retrieved_count": retrieved_count,
        "avg_score": round(avg_score, 4),
        "fallback_type": fallback_type,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    correct = sum(1 for row in results if row["correct"])
    wrong_direct = [
        row for row in results
        if row["gold_verdict"] == "mentor_needed" and row["predicted_verdict"] == "llm_direct"
    ]
    out = {
        "case_count": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "gold_counts": dict(Counter(row["gold_verdict"] for row in results)),
        "predicted_counts": dict(Counter(row["predicted_verdict"] for row in results)),
        "raw_predicted_counts": dict(Counter(row["raw_predicted_verdict"] for row in results)),
        "fallback_counts": dict(Counter(str(row.get("fallback_type") or "none") for row in results)),
        "wrong_direct_count": len(wrong_direct),
        "wrong_direct_case_ids": [row["case_id"] for row in wrong_direct],
        "per_label": {},
        "subtype_recall": {},
    }
    for label in BINARY_LABELS:
        tp = sum(1 for row in results if row["gold_verdict"] == label and row["predicted_verdict"] == label)
        fp = sum(1 for row in results if row["gold_verdict"] != label and row["predicted_verdict"] == label)
        fn = sum(1 for row in results if row["gold_verdict"] == label and row["predicted_verdict"] != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out["per_label"][label] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    for subtype in sorted(set(row["subtype"] for row in results)):
        rows = [row for row in results if row["subtype"] == subtype]
        out["subtype_recall"][subtype] = round(sum(1 for row in rows if row["correct"]) / len(rows), 4)
    return out


def metric(summary: dict[str, Any], label: str, name: str) -> float:
    return float(summary.get("per_label", {}).get(label, {}).get(name, 0.0))


def selection_key(row: dict[str, Any]) -> tuple:
    summary = row["summary"]
    return (
        -summary["wrong_direct_count"],
        metric(summary, "llm_direct", "recall"),
        summary["accuracy"],
        summary.get("subtype_recall", {}).get("llm_direct_general", 0.0),
    )


def render_html(payload: dict[str, Any]) -> str:
    rows = []
    for run in payload["runs"]:
        cfg = run["config"]
        s = run["summary"]
        rows.append(
            "<tr>"
            f"<td>{cfg['sim_threshold']:.2f}</td>"
            f"<td>{cfg['direct_threshold']:.2f}</td>"
            f"<td>{cfg['general_direct_confidence']:.2f}</td>"
            f"<td>{s['accuracy']:.4f}</td>"
            f"<td>{s['wrong_direct_count']}</td>"
            f"<td>{metric(s, 'llm_direct', 'precision'):.4f}</td>"
            f"<td>{metric(s, 'llm_direct', 'recall'):.4f}</td>"
            f"<td>{metric(s, 'mentor_needed', 'recall'):.4f}</td>"
            f"<td>{s['subtype_recall'].get('llm_direct_db', 0):.4f}</td>"
            f"<td>{s['subtype_recall'].get('llm_direct_general', 0):.4f}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>Cached Agent2 Grid</title>
<style>body{{font-family:Arial,sans-serif;margin:32px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border:1px solid #ddd;padding:8px;text-align:right}}th{{background:#f4f6f8}}</style>
</head><body><h1>Cached Agent2 Grid Search</h1><table><thead><tr>
<th>sim</th><th>direct</th><th>general conf</th><th>accuracy</th><th>wrong_direct</th><th>direct precision</th><th>direct recall</th><th>mentor recall</th><th>db recall</th><th>general recall</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-cache", type=Path, default=RETRIEVAL_CACHE)
    parser.add_argument("--llm-cache", type=Path, default=LLM_CACHE)
    parser.add_argument("--assets", type=Path, default=ASSETS_JSON)
    parser.add_argument("--sim-values", default="0.40,0.45,0.50,0.55")
    parser.add_argument("--direct-values", default="0.60,0.65,0.70,0.75")
    parser.add_argument("--general-confidence-values", default="0.75,0.80,0.85")
    parser.add_argument("--model", default=os.environ.get("AGENT2_OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--disable-general-direct", action="store_true")
    args = parser.parse_args()

    load_env_files()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for verifier/gate calls.")
    os.environ["AGENT2_OPENAI_MODEL"] = args.model

    retrieval_cache_path = args.retrieval_cache if args.retrieval_cache.is_absolute() else ROOT / args.retrieval_cache
    llm_cache_path = args.llm_cache if args.llm_cache.is_absolute() else ROOT / args.llm_cache
    assets_path = args.assets if args.assets.is_absolute() else ROOT / args.assets

    retrieval_cache = load_json(retrieval_cache_path)
    cases = retrieval_cache["cases"]
    if args.limit is not None:
        cases = cases[: args.limit]
    assets_by_id = {
        item["answer_id"]: item
        for item in load_json(assets_path).get("records", [])
        if item.get("embedding")
    }
    llm_cache = load_json(llm_cache_path, {"verify": {}, "general_gate": {}})
    llm_cache.setdefault("verify", {})
    llm_cache.setdefault("general_gate", {})

    agent = DecisionOnlyAgent()
    runs = []
    combos = [
        (sim, direct, conf)
        for sim in parse_float_list(args.sim_values)
        for direct in parse_float_list(args.direct_values)
        for conf in parse_float_list(args.general_confidence_values)
    ]
    for idx, (sim, direct, conf) in enumerate(combos, start=1):
        print(f"[cached grid {idx:03d}/{len(combos):03d}] sim={sim:.2f} direct={direct:.2f} conf={conf:.2f}")
        results = [
            evaluate_case(agent, llm_cache, case, assets_by_id, sim, direct, conf, args.disable_general_direct, args.model)
            for case in cases
        ]
        write_json(llm_cache_path, llm_cache)
        runs.append({
            "config": {
                "sim_threshold": sim,
                "direct_threshold": direct,
                "general_direct_confidence": conf,
            },
            "summary": summarize(results),
            "results": results,
        })

    best = sorted(runs, key=selection_key, reverse=True)[0]
    payload = {
        "description": "Cached Agent2 Itda threshold grid search.",
        "retrieval_cache": str(retrieval_cache_path),
        "llm_cache": str(llm_cache_path),
        "model": args.model,
        "best": best,
        "runs": runs,
        "llm_cache_counts": {
            "verify": len(llm_cache["verify"]),
            "general_gate": len(llm_cache["general_gate"]),
        },
    }
    write_json(SUMMARY_JSON, payload)
    REPORT_HTML.write_text(render_html(payload), encoding="utf-8")
    print(json.dumps({
        "summary": str(SUMMARY_JSON),
        "report": str(REPORT_HTML),
        "model": args.model,
        "best": {
            "config": best["config"],
            "summary": best["summary"],
        },
        "llm_cache_counts": payload["llm_cache_counts"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
