"""
Build Agent2 validation candidates from cleaned real Q&A data.

Outputs:
  data/cleaned/example_qa_asset_candidates.json
  eval/agent2_realqa_retrieval_candidates.json

This script does not mutate json_db/*.json. It creates an offline corpus and
retrieval result file that can be labeled later.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.embedding import get_embedding, top_k_similar  # noqa: E402


CLEAN_JSON = ROOT / "data" / "cleaned" / "example_qa_clean.json"
ASSET_JSON = ROOT / "data" / "cleaned" / "example_qa_asset_candidates.json"
OUTPUT_JSON = ROOT / "eval" / "agent2_realqa_retrieval_candidates.json"


def load_clean_records(limit: int | None = None) -> list[dict]:
    data = json.loads(CLEAN_JSON.read_text(encoding="utf-8"))
    records = data.get("records", [])
    if limit is not None:
        records = records[:limit]
    return records


def embedding_text_for_asset(record: dict) -> str:
    return "\n".join(filter(None, [
        f"분야: {record.get('domain', '')}",
        f"질문 제목: {record.get('title', '')}",
        f"멘티 질문: {record.get('mentee_question', '')}",
        f"멘토 답변 요약: {record.get('answer_summary', '')}",
    ]))


def embedding_text_for_query(record: dict) -> str:
    return "\n".join(filter(None, [
        f"분야: {record.get('domain', '')}",
        f"질문 제목: {record.get('title', '')}",
        record.get("mentee_question", ""),
    ]))


def build_assets(
    records: list[dict],
    reuse_cache: bool = True,
    metadata_only: bool = False,
) -> list[dict]:
    cached_by_id: dict[str, dict] = {}
    if reuse_cache and ASSET_JSON.exists():
        cached = json.loads(ASSET_JSON.read_text(encoding="utf-8")).get("records", [])
        cached_by_id = {item.get("answer_id"): item for item in cached if item.get("embedding")}

    assets: list[dict] = []
    for idx, record in enumerate(records, start=1):
        answer_id = record["record_id"]
        cached = cached_by_id.get(answer_id)
        if metadata_only:
            embedding = None
        elif cached:
            embedding = cached["embedding"]
        else:
            print(f"[asset embedding {idx:03d}/{len(records):03d}] {answer_id} {record.get('title', '')[:45]}")
            embedding = get_embedding(embedding_text_for_asset(record))

        assets.append({
            "answer_id": answer_id,
            "session_id": f"realqa_{answer_id}",
            "mentor_id": "realqa_mentor_unknown",
            "question_content": record.get("title", ""),
            "answer_content": record.get("mentor_answer", ""),
            "answer_summarize": record.get("answer_summary", ""),
            "domain_tags": [record.get("domain", "미분류")],
            "embedding": embedding,
            "is_assetized": True,
            "reuse_count": 0,
            "satisfaction_score": None,
            "created_at": None,
            "_source": "example_data.csv",
            "_record_id": record["record_id"],
            "_source_row": record.get("source_row"),
            "_mentee_question": record.get("mentee_question", ""),
            "_privacy_flags": record.get("privacy_flags", []),
        })
    return assets


def compact_answer(asset: dict, rank: int, score: float) -> dict:
    return {
        "answer_id": asset["answer_id"],
        "rank": rank,
        "similarity": round(score, 6),
        "domain_tags": asset.get("domain_tags", []),
        "question_content": asset.get("question_content", ""),
        "summary": asset.get("answer_summarize", ""),
    }


def build_candidates(records: list[dict], assets: list[dict], k: int) -> list[dict]:
    candidates: list[dict] = []
    for idx, record in enumerate(records, start=1):
        print(f"[query retrieval {idx:03d}/{len(records):03d}] {record['record_id']} {record.get('title', '')[:45]}")
        query_vec = get_embedding(embedding_text_for_query(record))
        top = top_k_similar(query_vec, assets, vec_field="embedding", k=max(k, len(assets)))

        top_k = top[:k]
        top_k_excluding_source = [
            item for item in top if item[0].get("answer_id") != record["record_id"]
        ][:k]

        source_rank = None
        source_similarity = None
        for rank, (asset, score) in enumerate(top, start=1):
            if asset.get("answer_id") == record["record_id"]:
                source_rank = rank
                source_similarity = score
                break

        similarities = [score for _, score in top_k]
        candidates.append({
            "case_id": record["record_id"],
            "domain": record.get("domain", "미분류"),
            "title": record.get("title", ""),
            "query": record.get("mentee_question", ""),
            "source_answer_id": record["record_id"],
            "source_answer_rank": source_rank,
            "source_answer_similarity": round(source_similarity, 6) if source_similarity is not None else None,
            "retrieved_answers": [
                compact_answer(asset, rank, score)
                for rank, (asset, score) in enumerate(top_k, start=1)
            ],
            "retrieved_answers_excluding_source": [
                compact_answer(asset, rank, score)
                for rank, (asset, score) in enumerate(top_k_excluding_source, start=1)
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
                "verdict": None,
                "usable_answer_ids": [],
                "reason": "",
                "label_status": "unlabeled",
            },
        })
    return candidates


def build_summary(candidates: list[dict]) -> dict:
    ranks = [
        item["source_answer_rank"]
        for item in candidates
        if isinstance(item.get("source_answer_rank"), int)
    ]
    top1 = sum(1 for item in candidates if item["features"]["source_answer_in_top1"])
    top5 = sum(1 for item in candidates if item["features"]["source_answer_in_top5"])
    top1_sims = [item["features"]["top1_similarity"] for item in candidates]
    return {
        "case_count": len(candidates),
        "source_answer_top1_count": top1,
        "source_answer_top1_rate": round(top1 / len(candidates), 4) if candidates else 0.0,
        "source_answer_top5_count": top5,
        "source_answer_top5_rate": round(top5 / len(candidates), 4) if candidates else 0.0,
        "source_answer_rank_median": statistics.median(ranks) if ranks else None,
        "top1_similarity_avg": round(sum(top1_sims) / len(top1_sims), 6) if top1_sims else 0.0,
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N clean records")
    parser.add_argument("--k", type=int, default=5, help="Number of retrieved answers per query")
    parser.add_argument("--no-cache", action="store_true", help="Ignore existing asset embedding cache")
    parser.add_argument("--metadata-only", action="store_true", help="Create asset candidates without embeddings/retrieval")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT.parent / ".env")
    load_dotenv(ROOT.parent / ".env.local")

    records = load_clean_records(limit=args.limit)
    metadata_only = args.metadata_only or not os.environ.get("OPENAI_API_KEY")
    if metadata_only and not args.metadata_only:
        print("OPENAI_API_KEY is not set. Writing metadata-only asset candidates; retrieval candidates are skipped.")

    assets = build_assets(records, reuse_cache=not args.no_cache, metadata_only=metadata_only)
    write_json(ASSET_JSON, {"description": "Asset candidates from example_data.csv", "records": assets})

    if metadata_only:
        print(json.dumps({
            "asset_candidates": str(ASSET_JSON),
            "retrieval_candidates": None,
            "summary": {
                "case_count": len(records),
                "status": "metadata_only",
                "reason": "OPENAI_API_KEY missing" if not os.environ.get("OPENAI_API_KEY") else "--metadata-only",
            },
        }, ensure_ascii=False, indent=2))
        return

    candidates = build_candidates(records, assets, k=args.k)
    summary = build_summary(candidates)
    write_json(OUTPUT_JSON, {
        "description": "Agent2 real Q&A retrieval candidates. Gold labels are intentionally blank.",
        "source_clean_json": str(CLEAN_JSON),
        "asset_candidates_json": str(ASSET_JSON),
        "summary": summary,
        "cases": candidates,
    })
    print(json.dumps({
        "asset_candidates": str(ASSET_JSON),
        "retrieval_candidates": str(OUTPUT_JSON),
        "summary": summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
