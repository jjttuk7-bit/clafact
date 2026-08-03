"""KOSIS 통계표 후보 검색의 재현 가능한 평가."""
from __future__ import annotations

from collections.abc import Callable


def evaluate_table_mapping(
    rows: list[dict],
    search: Callable[[str, int], list[dict]],
    *,
    top_k: int = 5,
) -> dict:
    """골든 표 ID와 후보 표 랭킹을 비교해 사례별 근거와 Hit@K를 남긴다."""
    cases = []
    summary = {
        "evaluated": 0,
        "skipped_no_kosis_gold": 0,
        "hit_any_at_1": 0,
        "hit_all_at_1": 0,
        "hit_any_at_k": 0,
        "hit_all_at_k": 0,
    }
    for row in rows:
        gold = list(row.get("gold_table_ids") or [])
        if not gold:
            summary["skipped_no_kosis_gold"] += 1
            continue
        candidates = search(row["sentence"], top_k)
        candidate_ids = [str(item.get("TBL_ID", "")) for item in candidates]
        top_one = candidate_ids[:1]
        any_at_1 = any(table_id in top_one for table_id in gold)
        all_at_1 = all(table_id in top_one for table_id in gold)
        any_at_k = any(table_id in candidate_ids for table_id in gold)
        all_at_k = all(table_id in candidate_ids for table_id in gold)
        summary["evaluated"] += 1
        summary["hit_any_at_1"] += any_at_1
        summary["hit_all_at_1"] += all_at_1
        summary["hit_any_at_k"] += any_at_k
        summary["hit_all_at_k"] += all_at_k
        cases.append({
            "candidate_id": row.get("candidate_id", ""),
            "sentence": row["sentence"],
            "gold_table_ids": gold,
            "candidate_table_ids": candidate_ids,
            "candidates": candidates,
            "hit_any_at_1": any_at_1,
            "hit_all_at_1": all_at_1,
            "hit_any_at_k": any_at_k,
            "hit_all_at_k": all_at_k,
        })
    return {"top_k": top_k, "summary": summary, "cases": cases}
