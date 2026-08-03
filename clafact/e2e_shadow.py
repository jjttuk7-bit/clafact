"""Attach persisted E2E verdicts to matching Shadow sentence rows."""
from __future__ import annotations

from collections.abc import Mapping, Sequence


def e2e_comparisons_by_row(
    run: Mapping[str, object], verdicts: Sequence[Mapping[str, object]],
) -> dict[int, list[dict[str, object]]]:
    """Convert sentence-matched E2E verdicts to the Shadow CSV comparison contract."""
    by_sentence = {
        str(verdict.get("sentence", "")).strip(): verdict
        for verdict in verdicts if str(verdict.get("sentence", "")).strip()
    }
    attached: dict[int, list[dict[str, object]]] = {}
    for row in run.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        verdict = by_sentence.get(str(row.get("sentence", "")).strip())
        if verdict is None:
            continue
        snapshot_ids = " | ".join(str(value) for value in verdict.get("snapshot_ids", []))
        attached[int(row["row_index"])] = [{
            "status": str(verdict.get("verdict", "not_comparable")),
            "reason": str(verdict.get("reason", "")),
            "claim_value": str(verdict.get("claimed", "")),
            "official_value": str(verdict.get("official", "")),
            "claim_period": str(verdict.get("claim_period", "")),
            "snapshot_id": snapshot_ids,
            "gate_results": [{"name": "E2E 원본", "passed": bool(snapshot_ids), "detail": "원본 스냅샷 기반 판정"}],
        }]
    return attached
