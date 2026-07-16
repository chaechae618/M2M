"""
Compare three Agent2 methods on the same Itda split.

Methods:
  1. old_baseline
     - current hardcoded thresholds
     - general-direct gate disabled
  2. current_baseline
     - current hardcoded thresholds
     - general-direct gate enabled
  3. grid_search_best
     - thresholds chosen from validation grid search
     - general-direct gate enabled

By default this compares on validation. Use --dataset eval/agent2_itda_eval.json
only after choosing the final method/thresholds.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
EVALUATE_SCRIPT = ROOT / "eval" / "evaluate_agent2_itda.py"
DEFAULT_DATASET = ROOT / "eval" / "agent2_itda_validation.json"
DEFAULT_ASSETS = ROOT / "json_db" / "mentor_answers.json"
GRID_SUMMARY = ROOT / "eval" / "agent2_itda_threshold_grid_summary.json"
OUT_DIR = ROOT / "eval" / "itda_method_comparison"
SUMMARY_JSON = ROOT / "eval" / "agent2_itda_method_comparison_summary.json"
REPORT_HTML = ROOT / "eval" / "agent2_itda_method_comparison_report.html"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_eval(
    name: str,
    args: list[str],
    dataset: Path,
    assets: Path,
    limit: int | None,
    model: str,
    out_dir: Path,
) -> dict[str, Any]:
    output = out_dir / f"{name}.json"
    cmd = [
        PYTHON,
        str(EVALUATE_SCRIPT),
        "--dataset", str(dataset),
        "--assets", str(assets),
        "--output", str(output),
        "--model", model,
        *args,
    ]
    if limit is not None:
        cmd.extend(["--limit", str(limit)])
    print(f"[method] {name}")
    completed = subprocess.run(cmd, cwd=str(ROOT), text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} evaluation failed")
    data = load_json(output)
    return {
        "name": name,
        "output": str(output),
        "config": data.get("config", {}),
        "summary": data["summary"],
    }


def metric(row: dict[str, Any], label: str, name: str) -> float:
    return float(row["summary"].get("per_label", {}).get(label, {}).get(name, 0.0))


def subtype(row: dict[str, Any], name: str) -> float:
    return float(row["summary"].get("subtype_recall", {}).get(name, 0.0))


def render_html(payload: dict[str, Any]) -> str:
    rows = []
    for row in payload["methods"]:
        s = row["summary"]
        rows.append(
            "<tr>"
            f"<td>{row['name']}</td>"
            f"<td>{s.get('case_count', 0)}</td>"
            f"<td>{s.get('accuracy', 0):.4f}</td>"
            f"<td>{s.get('wrong_direct_count', 0)}</td>"
            f"<td>{metric(row, 'llm_direct', 'precision'):.4f}</td>"
            f"<td>{metric(row, 'llm_direct', 'recall'):.4f}</td>"
            f"<td>{metric(row, 'mentor_needed', 'recall'):.4f}</td>"
            f"<td>{subtype(row, 'llm_direct_db'):.4f}</td>"
            f"<td>{subtype(row, 'llm_direct_general'):.4f}</td>"
            f"<td>{subtype(row, 'mentor_needed'):.4f}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>Agent2 Itda Method Comparison</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.5; color: #172033; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #d8deea; padding: 8px; text-align: right; }}
    th {{ background: #f2f5f9; }}
    td:first-child, th:first-child {{ text-align: left; }}
    .note {{ border: 1px solid #d8deea; padding: 14px; margin: 14px 0; }}
  </style>
</head>
<body>
  <h1>Agent2 Itda Method Comparison</h1>
  <div class="note">
    Dataset: {payload['dataset']}<br />
    Methods: old baseline, current baseline, grid-search best.
  </div>
  <table>
    <thead>
      <tr>
        <th>method</th>
        <th>cases</th>
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
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--grid-summary", type=Path, default=GRID_SUMMARY)
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--summary-output", type=Path, default=SUMMARY_JSON)
    parser.add_argument("--report-output", type=Path, default=REPORT_HTML)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    assets = args.assets if args.assets.is_absolute() else ROOT / args.assets
    grid_summary = args.grid_summary if args.grid_summary.is_absolute() else ROOT / args.grid_summary
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    summary_output = args.summary_output if args.summary_output.is_absolute() else ROOT / args.summary_output
    report_output = args.report_output if args.report_output.is_absolute() else ROOT / args.report_output
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)

    best_cfg = load_json(grid_summary)["best"]["config"]
    methods = [
        run_eval("old_baseline_no_general_direct", ["--disable-general-direct"], dataset, assets, args.limit, args.model, out_dir),
        run_eval("current_baseline_default_thresholds", [], dataset, assets, args.limit, args.model, out_dir),
        run_eval(
            "grid_search_best",
            [
                "--sim-search-first", str(best_cfg["sim_threshold"]),
                "--sim-mentor-first", str(best_cfg["sim_threshold"]),
                "--direct-search-first", str(best_cfg["direct_threshold"]),
                "--direct-mentor-first", str(best_cfg["direct_threshold"]),
                "--general-direct-confidence", str(best_cfg["general_direct_confidence"]),
            ],
            dataset,
            assets,
            args.limit,
            args.model,
            out_dir,
        ),
    ]

    payload = {
        "description": "Agent2 Itda method comparison.",
        "dataset": str(dataset),
        "assets": str(assets),
        "grid_best_config": best_cfg,
        "model": args.model,
        "methods": methods,
    }
    write_json(summary_output, payload)
    report_output.write_text(render_html(payload), encoding="utf-8")
    print(json.dumps({
        "summary_json": str(summary_output),
        "report_html": str(report_output),
        "methods": [
            {
                "name": row["name"],
                "accuracy": row["summary"].get("accuracy"),
                "wrong_direct": row["summary"].get("wrong_direct_count"),
                "direct_recall": row["summary"].get("per_label", {}).get("llm_direct", {}).get("recall"),
            }
            for row in methods
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
