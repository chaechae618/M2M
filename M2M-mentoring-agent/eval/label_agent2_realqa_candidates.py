"""
Create initial LLM labels for Agent2 real Q&A retrieval candidates.

Input:
  eval/agent2_realqa_retrieval_candidates.json
  data/cleaned/example_qa_asset_candidates.json

Output:
  eval/agent2_realqa_labeled_initial.json

The output is an initial labeling pass. Human review is still required,
especially for direct-answer labels and boundary cases.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "eval" / "agent2_realqa_retrieval_candidates.json"
ASSET_JSON = ROOT / "data" / "cleaned" / "example_qa_asset_candidates.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_realqa_labeled_initial.json"

MODEL = "gpt-4o-mini"


SYSTEM_PROMPT = """너는 멘토링 서비스의 Agent2 validation dataset 라벨러다.
목표는 검색된 기존 멘토 답변만으로 AI가 어느 수준까지 답변해도 되는지 보수적으로 판단하는 것이다.

반드시 세 가지 중 하나로 verdict를 고른다.

llm_direct:
- 검색된 답변들이 질문의 핵심을 충분히 커버한다.
- 개인 상황 판단, 실제 자료 검토, 회사/직무 특수성 판단이 핵심이 아니다.
- AI가 기존 답변 근거를 종합해 일반화된 답변을 제공해도 안전하다.

partial_with_mentor_suggest:
- 검색된 답변으로 일반 방향, 준비법, 일부 조언은 가능하다.
- 하지만 개인 배경, 구체 이력, 포트폴리오/자소서/면접 상황, 특정 회사/산업 맥락은 멘토 검토가 더 적합하다.

mentor_needed:
- 질문의 핵심이 개인 가능성 판단, 이력/스펙 평가, 자료 직접 피드백, 구체적 선택 조언, 민감한 현직 경험에 있다.
- 검색 결과가 있어도 질문의 핵심 판단을 대체하기 어렵다.
- 애매하면 mentor_needed 또는 partial_with_mentor_suggest를 택하고, llm_direct는 엄격하게 제한한다.

usable_answer_ids:
- 실제 답변 근거로 쓸 수 있는 answer_id만 고른다.
- 관련성이 약하거나 다른 맥락이면 제외한다.
- mentor_needed라도 일부 참고 가능한 답변이 있으면 넣을 수 있다. 단, 완전히 부족하면 빈 배열.

출력은 JSON만 반환한다.
"""


USER_PROMPT = """아래 케이스에 대해 Agent2 validation label 초안을 만들어라.

[멘티 질문]
{query}

[검색된 답변 Top-K]
{retrieved_answers}

[source answer 정보]
- 원래 이 질문에 대응되던 실제 답변 ID: {source_answer_id}
- 검색 순위: {source_answer_rank}
- 유사도: {source_answer_similarity}

[출력 JSON 형식]
{{
  "verdict": "llm_direct | partial_with_mentor_suggest | mentor_needed",
  "usable_answer_ids": ["answer_id"],
  "reason": "판단 근거 1~2문장",
  "confidence": 0.0,
  "review_priority": "high | medium | low",
  "hard_case_flags": {{
    "requires_artifact_review": true/false,
    "recency_sensitive": true/false,
    "personal_dependency_high": true/false,
    "specific_company_or_role_context": true/false
  }}
}}
"""


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compact_text(text: str, limit: int = 1400) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def build_asset_map() -> dict[str, dict]:
    assets = load_json(ASSET_JSON).get("records", [])
    return {item["answer_id"]: item for item in assets}


def build_retrieved_block(case: dict, asset_map: dict[str, dict], include_answer: bool) -> str:
    blocks: list[str] = []
    for item in case.get("retrieved_answers", []):
        asset = asset_map.get(item["answer_id"], {})
        lines = [
            f"- rank: {item.get('rank')}",
            f"  answer_id: {item.get('answer_id')}",
            f"  similarity: {item.get('similarity')}",
            f"  domain_tags: {item.get('domain_tags', [])}",
            f"  question_content: {item.get('question_content', '')}",
            f"  summary: {item.get('summary', '')}",
        ]
        if include_answer:
            lines.append(f"  answer_excerpt: {compact_text(asset.get('answer_content', ''))}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def parse_label(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    data = json.loads(raw)
    verdict = data.get("verdict")
    if verdict not in {"llm_direct", "partial_with_mentor_suggest", "mentor_needed"}:
        raise ValueError(f"invalid verdict: {verdict}")
    if not isinstance(data.get("usable_answer_ids"), list):
        data["usable_answer_ids"] = []
    confidence = data.get("confidence", 0.0)
    try:
        data["confidence"] = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        data["confidence"] = 0.0
    if data.get("review_priority") not in {"high", "medium", "low"}:
        data["review_priority"] = "high"
    data.setdefault("reason", "")
    data.setdefault("hard_case_flags", {})
    data["label_status"] = "llm_initial"
    return data


def label_case(client: OpenAI, case: dict, asset_map: dict[str, dict], include_answer: bool) -> dict:
    prompt = USER_PROMPT.format(
        query=case.get("query", ""),
        retrieved_answers=build_retrieved_block(case, asset_map, include_answer=include_answer),
        source_answer_id=case.get("source_answer_id"),
        source_answer_rank=case.get("source_answer_rank"),
        source_answer_similarity=case.get("source_answer_similarity"),
    )
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return parse_label(response.choices[0].message.content or "{}")


def load_existing_cases() -> dict[str, dict]:
    if not OUTPUT_JSON.exists():
        return {}
    data = load_json(OUTPUT_JSON)
    return {
        case["case_id"]: case
        for case in data.get("cases", [])
        if case.get("gold", {}).get("label_status") == "llm_initial"
    }


def build_summary(cases: list[dict]) -> dict:
    verdict_counts = Counter(case.get("gold", {}).get("verdict") for case in cases)
    review_counts = Counter(case.get("gold", {}).get("review_priority") for case in cases)
    return {
        "case_count": len(cases),
        "verdict_counts": dict(verdict_counts),
        "review_priority_counts": dict(review_counts),
        "model": MODEL,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-answer-excerpts", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.1)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT.parent / ".env")
    load_dotenv(ROOT.parent / ".env.local")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required.", file=sys.stderr)
        sys.exit(1)

    source = load_json(INPUT_JSON)
    cases = source.get("cases", [])
    if args.limit is not None:
        cases = cases[:args.limit]

    asset_map = build_asset_map()
    existing = load_existing_cases()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    labeled_cases: list[dict] = []
    for idx, case in enumerate(cases, start=1):
        case_id = case["case_id"]
        if case_id in existing:
            labeled_cases.append(existing[case_id])
            print(f"[skip labeled {idx:03d}/{len(cases):03d}] {case_id}")
            continue

        print(f"[label {idx:03d}/{len(cases):03d}] {case_id} {case.get('title', '')[:45]}")
        labeled = dict(case)
        for attempt in range(3):
            try:
                labeled["gold"] = label_case(
                    client,
                    case,
                    asset_map,
                    include_answer=not args.no_answer_excerpts,
                )
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                wait = 2 ** attempt
                print(f"  retry after error: {exc} (sleep {wait}s)")
                time.sleep(wait)
        labeled_cases.append(labeled)

        output = {
            **{k: v for k, v in source.items() if k != "cases"},
            "description": "Agent2 real Q&A retrieval candidates with initial LLM labels. Requires human review.",
            "label_summary": build_summary(labeled_cases),
            "cases": labeled_cases,
        }
        write_json(OUTPUT_JSON, output)
        time.sleep(args.sleep)

    final_output = {
        **{k: v for k, v in source.items() if k != "cases"},
        "description": "Agent2 real Q&A retrieval candidates with initial LLM labels. Requires human review.",
        "label_summary": build_summary(labeled_cases),
        "cases": labeled_cases,
    }
    write_json(OUTPUT_JSON, final_output)
    print(json.dumps({
        "output": str(OUTPUT_JSON),
        "label_summary": final_output["label_summary"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
