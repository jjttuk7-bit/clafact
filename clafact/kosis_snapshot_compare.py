"""Compare two immutable KOSIS evidence snapshots."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class KosisSnapshotComparison:
    added_count: int
    changed_count: int
    removed_count: int
    rows: tuple[Mapping[str, object], ...]


def _record_key(record: Mapping[str, Any]) -> tuple[str, str, str]:
    selection = json.dumps(record.get("selection", {}), ensure_ascii=False, sort_keys=True)
    return str(record.get("period", "")), str(record.get("indicator", "")), selection


def compare_snapshots(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> KosisSnapshotComparison:
    """Compare snapshot records by period, indicator, and selected dimensions."""
    before_records = {_record_key(record): record for record in before.get("records", [])}
    after_records = {_record_key(record): record for record in after.get("records", [])}
    rows: list[dict[str, object]] = []
    added_count = changed_count = removed_count = 0

    for key in sorted(set(before_records) | set(after_records)):
        old = before_records.get(key)
        new = after_records.get(key)
        if old is None:
            added_count += 1
            change_type = "added"
        elif new is None:
            removed_count += 1
            change_type = "removed"
        elif (
            str(old.get("value", "")) != str(new.get("value", ""))
            or str(old.get("last_changed_at", "")) != str(new.get("last_changed_at", ""))
        ):
            changed_count += 1
            change_type = "changed"
        else:
            continue
        reference = new or old or {}
        rows.append({
            "change_type": change_type,
            "period": reference.get("period", ""),
            "indicator": reference.get("indicator", ""),
            "selection": reference.get("selection", {}),
            "value_before": old.get("value", "") if old else "",
            "value_after": new.get("value", "") if new else "",
            "last_changed_before": old.get("last_changed_at", "") if old else "",
            "last_changed_after": new.get("last_changed_at", "") if new else "",
        })
    return KosisSnapshotComparison(
        added_count=added_count,
        changed_count=changed_count,
        removed_count=removed_count,
        rows=tuple(rows),
    )
