"""Immutable KOSIS snapshots to deterministic E2E verdict records."""
from __future__ import annotations

from collections.abc import Mapping

from clafact.eval.comparison_formula import evaluate_formula


def _first_value(snapshot: Mapping[str, object]) -> float:
    records = snapshot.get("records", [])
    if not isinstance(records, list) or not records:
        raise ValueError("스냅샷에 비교할 원본값이 없습니다.")
    return float(records[0]["value"])


def evaluate_change_rate_snapshots(
    *,
    candidate_id: str,
    claimed: float,
    base_snapshot: Mapping[str, object],
    current_snapshot: Mapping[str, object],
    tolerance: float = 0.05,
) -> dict[str, object]:
    """두 단일값 스냅샷의 전년동월비를 재현 가능한 판정 기록으로 만든다."""
    result = evaluate_formula(
        "change_rate", claimed=claimed,
        values={"base": _first_value(base_snapshot), "current": _first_value(current_snapshot)},
        tolerance=tolerance,
    )
    return {
        "candidate_id": candidate_id,
        "formula": "change_rate",
        "claimed": claimed,
        "official": result.official_value,
        "verdict": result.status,
        "reason": result.reason,
        "snapshot_ids": [str(base_snapshot["snapshot_id"]), str(current_snapshot["snapshot_id"])],
    }
