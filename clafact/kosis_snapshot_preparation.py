"""Assemble KOSIS evidence drafts and reproducible snapshot inputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from clafact.kosis_evidence_autofill import KosisAutofillFields, autofill_from_rows
from clafact.kosis_table_structure import KosisTableStructure, classify_table_structure


@dataclass(frozen=True)
class KosisSnapshotPreparation:
    """Prepared, API-free inputs for a later evidence snapshot save."""

    fields: KosisAutofillFields
    structure: KosisTableStructure
    snapshot_context: Mapping[str, object]


def prepare_kosis_snapshot_context(
    *,
    table_id: str,
    org_id: str,
    rows: Sequence[Mapping[str, object]],
    retrieved_at: str,
) -> KosisSnapshotPreparation:
    """Build the existing evidence draft and snapshot context from fetched rows."""
    return KosisSnapshotPreparation(
        fields=autofill_from_rows(table_id=table_id, rows=rows),
        structure=classify_table_structure(rows),
        snapshot_context={
            "org_id": org_id,
            "table_id": table_id,
            "query_params": {"recent_n": 1},
            "retrieved_at": retrieved_at,
            "rows": list(rows),
        },
    )
