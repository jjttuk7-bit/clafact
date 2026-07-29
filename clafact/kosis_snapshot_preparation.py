"""Assemble KOSIS evidence drafts and reproducible snapshot inputs."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from clafact.kosis_evidence_autofill import KosisAutofillFields, autofill_from_rows
from clafact.kosis_table_structure import KosisTableStructure, classify_table_structure


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class KosisSnapshotContext:
    """Immutable snapshot inputs with a storage-compatible conversion method."""

    org_id: str
    table_id: str
    query_params: Mapping[str, object]
    retrieved_at: str
    rows: tuple[Mapping[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        """Return a fresh mutable payload accepted by the existing snapshot store."""
        return {
            "org_id": self.org_id,
            "table_id": self.table_id,
            "query_params": _thaw(self.query_params),
            "retrieved_at": self.retrieved_at,
            "rows": _thaw(self.rows),
        }


@dataclass(frozen=True)
class KosisSnapshotPreparation:
    """Prepared, API-free inputs for a later evidence snapshot save."""

    fields: KosisAutofillFields
    structure: KosisTableStructure
    snapshot_context: KosisSnapshotContext


def prepare_kosis_snapshot_context(
    *,
    table_id: str,
    org_id: str,
    rows: Sequence[Mapping[str, object]],
    retrieved_at: str,
    query_params: Mapping[str, object] | None = None,
) -> KosisSnapshotPreparation:
    """Build the existing evidence draft and immutable snapshot context from fetched rows."""
    frozen_rows = tuple(_freeze_mapping(row) for row in rows)
    frozen_query_params = _freeze_mapping(
        query_params if query_params is not None else {"recent_n": 1}
    )
    return KosisSnapshotPreparation(
        fields=autofill_from_rows(table_id=table_id, rows=rows),
        structure=classify_table_structure(rows),
        snapshot_context=KosisSnapshotContext(
            org_id=org_id,
            table_id=table_id,
            query_params=frozen_query_params,
            retrieved_at=retrieved_at,
            rows=frozen_rows,
        ),
    )