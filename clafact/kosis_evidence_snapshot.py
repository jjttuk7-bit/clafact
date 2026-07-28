"""Create immutable research snapshots of KOSIS API responses."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from clafact.kosis import build_url


@dataclass(frozen=True)
class KosisEvidenceSnapshot:
    snapshot_id: str
    table_id: str
    org_id: str
    query_params: Mapping[str, object]
    reproducible_url: str
    retrieved_at: str
    records: tuple[Mapping[str, object], ...]
    content_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "table_id": self.table_id,
            "org_id": self.org_id,
            "query_params": dict(self.query_params),
            "reproducible_url": self.reproducible_url,
            "retrieved_at": self.retrieved_at,
            "records": [dict(record) for record in self.records],
            "content_hash": self.content_hash,
        }


def _selection(row: Mapping[str, object]) -> dict[str, str]:
    selection: dict[str, str] = {}
    for level in range(1, 9):
        dimension = str(row.get(f"C{level}_OBJ_NM", "")).strip()
        value = str(row.get(f"C{level}_NM", "")).strip()
        if dimension and value:
            selection[dimension] = value
    return selection


def _record(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "period": str(row.get("PRD_DE", "")).strip(),
        "value": str(row.get("DT", "")).strip(),
        "unit": str(row.get("UNIT_NM", "")).strip(),
        "indicator": str(row.get("ITM_NM", "")).strip(),
        "last_changed_at": str(row.get("LST_CHN_DE", "")).strip(),
        "selection": _selection(row),
    }


def build_evidence_snapshot(
    *,
    org_id: str,
    table_id: str,
    query_params: Mapping[str, object],
    retrieved_at: str,
    rows: Sequence[Mapping[str, object]],
) -> KosisEvidenceSnapshot:
    """Build an immutable, key-safe KOSIS response snapshot for later reproduction."""
    records = tuple(_record(row) for row in rows)
    payload = {
        "table_id": table_id,
        "org_id": org_id,
        "query_params": dict(query_params),
        "retrieved_at": retrieved_at,
        "records": [dict(record) for record in records],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return KosisEvidenceSnapshot(
        snapshot_id=f"kosis-{content_hash[:16]}",
        table_id=table_id,
        org_id=org_id,
        query_params=dict(query_params),
        reproducible_url=build_url(org_id, table_id, **dict(query_params)),
        retrieved_at=retrieved_at,
        records=records,
        content_hash=content_hash,
    )
