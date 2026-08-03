"""E2E 실행의 실제 완료 범위를 과장 없이 요약한다."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def build_e2e_progress(
    rows: Iterable[Mapping[str, object]],
    *,
    catalog_table_ids: set[str],
    comparison_candidate_ids: set[str],
) -> dict:
    """표 메타·좌표/원본 스냅샷·판정의 완료 단계를 분리해 반환한다."""
    cases = []
    counts = {
        "total": 0,
        "verdict_verified": 0,
        "needs_coordinates_and_snapshot": 0,
        "needs_catalog": 0,
        "no_table_mapping": 0,
    }
    for row in rows:
        candidate_id = str(row.get("candidate_id", ""))
        table_ids = [str(value) for value in row.get("gold_table_ids", []) if str(value)]
        if candidate_id in comparison_candidate_ids:
            status = "verdict_verified"
        elif not table_ids:
            status = "no_table_mapping"
        elif not set(table_ids).issubset(catalog_table_ids):
            status = "needs_catalog"
        else:
            status = "needs_coordinates_and_snapshot"
        counts["total"] += 1
        counts[status] += 1
        cases.append({
            "candidate_id": candidate_id,
            "gold_table_ids": table_ids,
            "status": status,
        })
    return {"summary": counts, "cases": cases}
