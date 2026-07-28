"""Present KOSIS evidence objects and their research-only links as registry rows."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


STRUCTURE_LABELS = {
    "time_series": "시계열형",
    "regional_comparison": "지역 비교형",
    "crosstab": "교차표형",
    "indicator_bundle": "지표 묶음형",
    "unknown": "판정 보류",
}


def build_evidence_registry_rows(
    *,
    evidence_objects: Sequence[Mapping[str, Any]],
    snapshot_counts: Mapping[str, int],
    mapping_counts: Mapping[str, int],
    review_counts: Mapping[str, int],
) -> list[dict[str, object]]:
    """Build a team-reviewable registry without changing any research record."""
    rows: list[dict[str, object]] = []
    for evidence in evidence_objects:
        table_id = str(evidence["table_id"])
        evidence_id = str(evidence.get("evidence_id") or table_id)
        provenance = evidence.get("definition_provenance", {})
        rows.append({
            "근거 객체 ID": evidence_id,
            "통계표 ID": table_id,
            "표 제목": str(evidence.get("title", "")),
            "핵심 지표": str(evidence.get("indicator", "")),
            "구조 유형": STRUCTURE_LABELS.get(
                str(evidence.get("structure_type", "")), "미분류"
            ),
            "정의 승인": str(provenance.get("method", "-")),
            "스냅샷": snapshot_counts.get(table_id, 0),
            "Shadow 연결": mapping_counts.get(evidence_id, 0),
            "개정 검토": review_counts.get(table_id, 0),
        })
    return rows
