"""
LLM-gated simulation for a general-knowledge direct-answer route.

The gate asks whether a question can be answered directly from general career
knowledge without personal judgment, artifact review, or mentor-specific
experience. It then simulates promotion to llm_direct for safe candidates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from openai import OpenAI


ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "eval" / "agent2_usable_fallback_applied_results.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_general_direct_llm_gate_simulation.json"

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

PROMPT = """아래 진로 상담 질문이 멘토 연결 없이 AI가 일반 지식으로 직접 답변해도 안전한지 판정해줘.
반드시 JSON만 출력해.

[direct_general_allowed=true 기준]
- 일반적인 직무 정보, 준비 방법, 필요한 역량, 학습 방법, 직무 차이, 면접 준비 요소
- 특정 개인의 합격 가능성/적합성 판단이 아님
- 이력서/자소서/포트폴리오/작품을 실제로 봐야 하는 검토 요청이 아님
- 최신 채용 공고, 특정 회사 내부 정보, 개인 사정에 따른 의사결정이 핵심이 아님

[direct_general_allowed=false 기준]
- "내 상황에서", "저한테 맞나요", "가능할까요", "합격할까요" 같은 개인 판단
- 자료 첨삭/검토/평가가 필요한 질문
- 구체적인 경력 선택, 이직 가능성, 개인 스펙 판단
- 멘토의 실제 경험 확인이 핵심인 질문

[출력 형식]
{{"direct_general_allowed": true, "confidence": 0.0, "answer_mode": "general_direct 또는 mentor_needed", "risk_reason": "한 문장"}}

질문: {question}"""


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


def hard_flags(item: dict) -> dict:
    return item.get("retrieval_log", {}).get("hard_case_flags", {}) or {}


def top1_fallback_similarity(item: dict) -> float:
    fallback = item.get("retrieval_log", {}).get("usable_fallback") or {}
    try:
        return float(fallback.get("top1_similarity") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def eligible_for_gate(item: dict) -> bool:
    if item.get("predicted_verdict") == "llm_direct":
        return False
    if item.get("strategy") != "search_first":
        return False
    flags = hard_flags(item)
    if flags.get("requires_artifact_review") or flags.get("risk_flags"):
        return False
    question = item.get("title") or ""
    if not is_general_info_question(question):
        return False
    if item.get("fallback_type") == "no_similar_answers":
        return True
    if item.get("predicted_verdict") == "partial_with_mentor_suggest":
        top1 = top1_fallback_similarity(item)
        return 0.0 < top1 <= 0.65
    return False


def judge(client: OpenAI, question: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": PROMPT.format(question=question)}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT_JSON)
    args = parser.parse_args()

    source = load_json(INPUT_JSON)
    candidates = [item for item in source["results"] if eligible_for_gate(item)]
    if args.limit is not None:
        candidates = candidates[: args.limit]

    existing: dict[str, dict] = {}
    if args.resume and args.output.exists():
        existing_payload = load_json(args.output)
        existing = {
            item["case_id"]: item
            for item in existing_payload.get("gate_results", [])
        }

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    gate_results = list(existing.values())
    seen = set(existing)
    for idx, item in enumerate(candidates, start=1):
        if item["case_id"] in seen:
            continue
        print(f"[gate {idx}/{len(candidates)}] {item['case_id']} {item.get('title', '')}")
        decision = judge(client, item.get("title") or "")
        gate_results.append({
            "case_id": item["case_id"],
            "gold_verdict": item["gold_verdict"],
            "current_predicted_verdict": item["predicted_verdict"],
            "fallback_type": item.get("fallback_type"),
            "top1_fallback_similarity": top1_fallback_similarity(item),
            "question": item.get("title") or "",
            "gate": decision,
        })
        partial_payload = {
            "description": "LLM-gated simulation of general direct route.",
            "input": str(INPUT_JSON.relative_to(ROOT)),
            "candidate_count": len(candidates),
            "gate_results": gate_results,
        }
        write_json(args.output, partial_payload)

    allowed_ids = {
        item["case_id"]
        for item in gate_results
        if item.get("gate", {}).get("direct_general_allowed") is True
        and float(item.get("gate", {}).get("confidence") or 0.0) >= 0.8
    }

    updated = deepcopy(source["results"])
    for item in updated:
        if item["case_id"] in allowed_ids:
            item["predicted_verdict"] = "llm_direct"
            item["fallback_type"] = None
            item["fallback_reason"] = None
            item.setdefault("retrieval_log", {})["general_direct_llm_gate"] = {
                "promoted": True,
            }

    payload = {
        "description": "LLM-gated simulation of general direct route.",
        "input": str(INPUT_JSON.relative_to(ROOT)),
        "candidate_count": len(candidates),
        "allowed_count": len(allowed_ids),
        "allowed_case_ids": sorted(allowed_ids),
        "baseline_summary": source["summary"],
        "summary": summarize(updated),
        "gate_results": gate_results,
    }
    write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
