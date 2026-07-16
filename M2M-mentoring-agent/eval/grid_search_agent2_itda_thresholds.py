"""
Grid-search Agent2 thresholds on the Itda validation split.

Selection rule:
  1. minimize wrong_direct_count
  2. maximize llm_direct recall
  3. maximize accuracy
  4. maximize llm_direct_general recall

This script calls eval/evaluate_agent2_itda.py for each configuration because
the current Agent2 verifier is part of the routing decision.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
EVALUATE_SCRIPT = ROOT / "eval" / "evaluate_agent2_itda.py"
VALIDATION_JSON = ROOT / "eval" / "agent2_itda_validation.json"
DEFAULT_ASSETS = ROOT / "json_db" / "mentor_answers.json"
RESULT_DIR = ROOT / "eval" / "itda_threshold_runs"
SUMMARY_JSON = ROOT / "eval" / "agent2_itda_threshold_grid_summary.json"
REPORT_HTML = ROOT / "eval" / "agent2_itda_threshold_report.html"


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def metric(summary: dict[str, Any], label: str, name: str) -> float:
    return float(summary.get("per_label", {}).get(label, {}).get(name, 0.0))


def subtype(summary: dict[str, Any], name: str) -> float:
    return float(summary.get("subtype_recall", {}).get(name, 0.0))


def selection_key(row: dict[str, Any]) -> tuple:
    summary = row["summary"]
    return (
        -int(summary.get("wrong_direct_count", 999999)),
        metric(summary, "llm_direct", "recall"),
        float(summary.get("accuracy", 0.0)),
        subtype(summary, "llm_direct_general"),
    )


def run_one(
    dataset: Path,
    assets: Path,
    output: Path,
    sim: float,
    direct: float,
    general_conf: float,
    limit: int | None,
    model: str,
) -> dict[str, Any]:
    cmd = [
        PYTHON,
        str(EVALUATE_SCRIPT),
        "--dataset", str(dataset),
        "--assets", str(assets),
        "--output", str(output),
        "--sim-search-first", f"{sim:.4f}",
        "--sim-mentor-first", f"{sim:.4f}",
        "--direct-search-first", f"{direct:.4f}",
        "--direct-mentor-first", f"{direct:.4f}",
        "--general-direct-confidence", f"{general_conf:.4f}",
        "--model", model,
    ]
    if limit is not None:
        cmd.extend(["--limit", str(limit)])

    completed = subprocess.run(cmd, cwd=str(ROOT), text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"evaluation failed for sim={sim}, direct={direct}, general_conf={general_conf}")

    data = load_json(output)
    return {
        "config": {
            "sim_threshold": sim,
            "direct_threshold": direct,
            "general_direct_confidence": general_conf,
        },
        "output": str(output),
        "summary": data["summary"],
    }


def render_html(payload: dict[str, Any]) -> str:
    rows = payload["runs"]
    best = payload["best"]
    body_rows = []
    for row in rows:
        s = row["summary"]
        cfg = row["config"]
        body_rows.append(
            "<tr>"
            f"<td>{cfg['sim_threshold']:.2f}</td>"
            f"<td>{cfg['direct_threshold']:.2f}</td>"
            f"<td>{cfg['general_direct_confidence']:.2f}</td>"
            f"<td>{s.get('accuracy', 0):.4f}</td>"
            f"<td>{s.get('wrong_direct_count', 0)}</td>"
            f"<td>{metric(s, 'llm_direct', 'precision'):.4f}</td>"
            f"<td>{metric(s, 'llm_direct', 'recall'):.4f}</td>"
            f"<td>{metric(s, 'mentor_needed', 'recall'):.4f}</td>"
            f"<td>{subtype(s, 'llm_direct_db'):.4f}</td>"
            f"<td>{subtype(s, 'llm_direct_general'):.4f}</td>"
            f"<td>{subtype(s, 'mentor_needed'):.4f}</td>"
            "</tr>"
        )

    best_cfg = best["config"]
    best_summary = best["summary"]
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>Agent2 Itda Threshold Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.5; color: #172033; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #d8deea; padding: 8px; text-align: right; }}
    th {{ background: #f2f5f9; }}
    td:first-child, th:first-child {{ text-align: right; }}
    .box {{ border: 1px solid #d8deea; padding: 16px; margin: 16px 0; }}
    code {{ background: #f2f5f9; padding: 2px 4px; }}
  </style>
</head>
<body>
  <h1>Agent2 Itda Threshold Report</h1>
  <div class="box">
    <p><strong>Best config</strong></p>
    <p>
      retrieve sim threshold: <code>{best_cfg['sim_threshold']:.2f}</code><br />
      direct decision threshold: <code>{best_cfg['direct_threshold']:.2f}</code><br />
      general-direct confidence: <code>{best_cfg['general_direct_confidence']:.2f}</code>
    </p>
    <p>
      accuracy: <code>{best_summary.get('accuracy', 0):.4f}</code>,
      wrong_direct: <code>{best_summary.get('wrong_direct_count', 0)}</code>,
      llm_direct recall: <code>{metric(best_summary, 'llm_direct', 'recall'):.4f}</code>
    </p>
  </div>
  <table>
    <thead>
      <tr>
        <th>sim</th>
        <th>direct</th>
        <th>general conf</th>
        <th>accuracy</th>
        <th>wrong_direct</th>
        <th>direct precision</th>
        <th>direct recall</th>
        <th>mentor recall</th>
        <th>db direct recall</th>
        <th>general direct recall</th>
        <th>mentor subtype recall</th>
      </tr>
    </thead>
    <tbody>
      {''.join(body_rows)}
    </tbody>
  </table>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=VALIDATION_JSON)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--sim-values", default="0.40,0.45,0.50,0.55")
    parser.add_argument("--direct-values", default="0.60,0.65,0.70,0.75")
    parser.add_argument("--general-confidence-values", default="0.75,0.80,0.85")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    assets = args.assets if args.assets.is_absolute() else ROOT / args.assets
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    runs = []
    combos = list(itertools.product(
        parse_float_list(args.sim_values),
        parse_float_list(args.direct_values),
        parse_float_list(args.general_confidence_values),
    ))
    for idx, (sim, direct, general_conf) in enumerate(combos, start=1):
        output = RESULT_DIR / f"run_{idx:03d}_sim{sim:.2f}_direct{direct:.2f}_g{general_conf:.2f}.json"
        print(f"[grid {idx:03d}/{len(combos):03d}] sim={sim:.2f} direct={direct:.2f} general_conf={general_conf:.2f}")
        runs.append(run_one(dataset, assets, output, sim, direct, general_conf, args.limit, args.model))

    best = sorted(runs, key=selection_key, reverse=True)[0]
    payload = {
        "description": "Agent2 Itda validation threshold grid search.",
        "selection_rule": [
            "minimize wrong_direct_count",
            "maximize llm_direct recall",
            "maximize accuracy",
            "maximize llm_direct_general recall",
        ],
        "dataset": str(dataset),
        "assets": str(assets),
        "model": args.model,
        "best": best,
        "runs": runs,
    }
    write_json(SUMMARY_JSON, payload)
    REPORT_HTML.write_text(render_html(payload), encoding="utf-8")
    print(json.dumps({
        "summary_json": str(SUMMARY_JSON),
        "report_html": str(REPORT_HTML),
        "best": best,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
