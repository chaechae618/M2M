"""
Build synthetic llm_direct supplement cases for Agent2 validation.

This balances the real 상담 dataset, which is naturally dominated by
partial_with_mentor_suggest / mentor_needed labels.

Inputs:
  data/cleaned/example_qa_asset_candidates.json
  eval/agent2_realqa_labeled_initial.json

Outputs:
  eval/agent2_direct_supplement.json
  eval/agent2_balanced_with_direct_supplement.json
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
sys.path.insert(0, str(ROOT))

from utils.embedding import get_embedding, top_k_similar  # noqa: E402


ASSET_JSON = ROOT / "data" / "cleaned" / "example_qa_asset_candidates.json"
REALQA_LABELED_JSON = ROOT / "eval" / "agent2_realqa_labeled_initial.json"
SUPPLEMENT_JSON = ROOT / "eval" / "agent2_direct_supplement.json"
COMBINED_JSON = ROOT / "eval" / "agent2_balanced_with_direct_supplement.json"

MODEL = "gpt-4.1-mini"


SYSTEM_PROMPT = """너는 Agent2 validation dataset을 보강하는 데이터 생성기다.
목표는 llm_direct로 분류될 수 있는 일반 정보형 질문을 만드는 것이다.

입력으로 실제 멘토 답변 1개가 주어진다. 이 답변이 근거로 충분히 쓰일 수 있는
개인 맥락이 약한 질문을 1개 만들어라.

생성해야 하는 질문:
- 직무 정보, 준비 방법, 역량, 면접 일반론, 포트폴리오 일반 구성, 업무 이해처럼 일반화 가능해야 한다.
- "제 스펙으로 가능한가요", "저는 무엇을 선택해야 하나요", "첨부한 자소서/포트폴리오를 봐주세요" 같은 개인 판단 질문이면 안 된다.
- 특정 회사 합격 가능성, 개인 이력 평가, 실제 자료 피드백이 핵심이면 안 된다.
- 한국어 자연문으로 작성한다.

만약 주어진 답변이 너무 개인 피드백 중심이라 llm_direct 질문을 만들기 부적절하면 usable=false를 반환한다.

출력은 JSON만 반환한다.
"""


USER_PROMPT = """아래 멘토 답변을 근거로 llm_direct 가능한 일반 질문을 생성해라.

[분야]
{domain}

[원래 질문 제목]
{title}

[멘토 답변 요약]
{summary}

[멘토 답변 일부]
{answer_excerpt}

[출력 JSON 형식]
{{
  "usable": true/false,
  "query": "생성한 일반 질문",
  "reason": "왜 llm_direct로 적합한지 또는 부적합한지 1문장",
  "direct_answer_rationale": "검색된 답변만으로 AI 직접 답변이 가능한 이유 1문장"
}}
"""


SKIP_KEYWORDS = [
    "자소서",
    "이력서",
    "포트폴리오",
    "피드백",
    "가능할까요",
    "괜찮을까요",
    "선택",
    "합격",
    "탈락",
    "스펙",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compact(text: str, limit: int = 1500) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def build_summary(cases: list[dict]) -> dict:
    verdict_counts = Counter(case.get("gold", {}).get("verdict") for case in cases)
    return {
        "case_count": len(cases),
        "verdict_counts": dict(verdict_counts),
    }


def load_existing_supplement() -> list[dict]:
    if not SUPPLEMENT_JSON.exists():
        return []
    return load_json(SUPPLEMENT_JSON).get("cases", [])


def generate_direct_query(client: OpenAI, asset: dict) -> dict:
    prompt = USER_PROMPT.format(
        domain=", ".join(asset.get("domain_tags", [])),
        title=asset.get("question_content", ""),
        summary=asset.get("answer_summarize", ""),
        answer_excerpt=compact(asset.get("answer_content", "")),
    )
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(response.choices[0].message.content or "{}")
    data["usable"] = bool(data.get("usable"))
    data["query"] = (data.get("query") or "").strip()
    data.setdefault("reason", "")
    data.setdefault("direct_answer_rationale", "")
    return data


def compact_answer(asset: dict, rank: int, score: float) -> dict:
    return {
        "answer_id": asset["answer_id"],
        "rank": rank,
        "similarity": round(score, 6),
        "domain_tags": asset.get("domain_tags", []),
        "question_content": asset.get("question_content", ""),
        "summary": asset.get("answer_summarize", ""),
    }


def make_case(case_no: int, asset: dict, generated: dict, assets: list[dict], k: int) -> dict:
    query_vec = get_embedding(generated["query"])
    top = top_k_similar(query_vec, assets, vec_field="embedding", k=max(k, len(assets)))
    top_k = top[:k]

    source_rank = None
    source_similarity = None
    for rank, (candidate, score) in enumerate(top, start=1):
        if candidate["answer_id"] == asset["answer_id"]:
            source_rank = rank
            source_similarity = score
            break

    similarities = [score for _, score in top_k]
    usable_ids = [asset["answer_id"]]
    if source_rank is None or source_rank > k:
        usable_ids = [top_k[0][0]["answer_id"]] if top_k else []

    return {
        "case_id": f"direct_supp_{case_no:03d}",
        "domain": asset.get("domain_tags", ["미분류"])[0],
        "title": generated["query"],
        "query": generated["query"],
        "source_answer_id": asset["answer_id"],
        "source_answer_rank": source_rank,
        "source_answer_similarity": round(source_similarity, 6) if source_similarity is not None else None,
        "retrieved_answers": [
            compact_answer(candidate, rank, score)
            for rank, (candidate, score) in enumerate(top_k, start=1)
        ],
        "retrieved_answers_excluding_source": [
            compact_answer(candidate, rank, score)
            for rank, (candidate, score) in enumerate(
                [item for item in top if item[0]["answer_id"] != asset["answer_id"]][:k],
                start=1,
            )
        ],
        "features": {
            "source_answer_in_top1": source_rank == 1,
            "source_answer_in_top5": source_rank is not None and source_rank <= 5,
            "top1_similarity": round(similarities[0], 6) if similarities else 0.0,
            "topk_avg_similarity": round(sum(similarities) / len(similarities), 6) if similarities else 0.0,
            "similarity_gap": round(similarities[0] - similarities[1], 6) if len(similarities) >= 2 else 0.0,
            "retrieved_count": len(top_k),
        },
        "gold": {
            "verdict": "llm_direct",
            "usable_answer_ids": usable_ids,
            "reason": generated.get("direct_answer_rationale") or generated.get("reason", ""),
            "confidence": 0.85,
            "review_priority": "medium",
            "hard_case_flags": {
                "requires_artifact_review": False,
                "recency_sensitive": False,
                "personal_dependency_high": False,
                "specific_company_or_role_context": False,
            },
            "label_status": "synthetic_direct_seed",
        },
        "generation": {
            "source": "direct_supplement",
            "model": MODEL,
            "source_title": asset.get("question_content", ""),
            "generation_reason": generated.get("reason", ""),
        },
    }


def likely_general_asset(asset: dict) -> bool:
    text = f"{asset.get('question_content', '')} {asset.get('answer_summarize', '')}"
    hits = sum(1 for keyword in SKIP_KEYWORDS if keyword in text)
    return hits <= 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=45)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=0.1)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT.parent / ".env")
    load_dotenv(ROOT.parent / ".env.local")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required.", file=sys.stderr)
        sys.exit(1)

    assets = load_json(ASSET_JSON).get("records", [])
    assets = [asset for asset in assets if asset.get("embedding")]
    existing = load_existing_supplement()
    existing_sources = {case.get("source_answer_id") for case in existing}
    cases = list(existing)

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    case_no = len(cases) + 1
    for asset in assets:
        if len(cases) >= args.target:
            break
        if asset["answer_id"] in existing_sources:
            continue
        if not likely_general_asset(asset):
            continue

        print(f"[direct supplement {len(cases)+1:03d}/{args.target:03d}] {asset['answer_id']} {asset.get('question_content', '')[:45]}")
        generated = generate_direct_query(client, asset)
        if not generated.get("usable") or not generated.get("query"):
            print(f"  skip: {generated.get('reason', '')}")
            continue

        case = make_case(case_no, asset, generated, assets, k=args.k)
        cases.append(case)
        existing_sources.add(asset["answer_id"])
        case_no += 1

        write_json(SUPPLEMENT_JSON, {
            "description": "Synthetic llm_direct supplement cases for Agent2 validation.",
            "summary": build_summary(cases),
            "cases": cases,
        })
        time.sleep(args.sleep)

    supplement = {
        "description": "Synthetic llm_direct supplement cases for Agent2 validation.",
        "summary": build_summary(cases),
        "cases": cases,
    }
    write_json(SUPPLEMENT_JSON, supplement)

    realqa = load_json(REALQA_LABELED_JSON)
    combined_cases = realqa.get("cases", []) + cases
    combined = {
        "description": "Agent2 validation dataset with realQA labels and synthetic llm_direct supplement.",
        "realqa_source": str(REALQA_LABELED_JSON),
        "direct_supplement_source": str(SUPPLEMENT_JSON),
        "summary": build_summary(combined_cases),
        "realqa_summary": realqa.get("label_summary", {}),
        "direct_supplement_summary": supplement["summary"],
        "cases": combined_cases,
    }
    write_json(COMBINED_JSON, combined)
    print(json.dumps({
        "supplement": str(SUPPLEMENT_JSON),
        "combined": str(COMBINED_JSON),
        "summary": combined["summary"],
        "direct_supplement_summary": supplement["summary"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
