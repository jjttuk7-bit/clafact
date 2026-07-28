"""Traceable research evidence object for a KOSIS table."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class KosisEvidenceObject:
    table_id: str
    url: str
    title: str
    organization: str
    indicator: str
    dimensions: tuple[str, ...]
    time_dimension: str
    unit: str
    definition: str
    source_selection: Mapping[str, str]
    retrieved_at: str
    structure_type: str = ""
    snapshot_id: str = ""
    definition_provenance: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("table_id", "url", "title", "organization", "indicator", "retrieved_at"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} is required")

    def as_dict(self) -> dict[str, object]:
        return {
            "table_id": self.table_id,
            "url": self.url,
            "title": self.title,
            "organization": self.organization,
            "indicator": self.indicator,
            "dimensions": list(self.dimensions),
            "time_dimension": self.time_dimension,
            "unit": self.unit,
            "definition": self.definition,
            "source_selection": dict(self.source_selection),
            "retrieved_at": self.retrieved_at,
            "structure_type": self.structure_type,
            "snapshot_id": self.snapshot_id,
            "definition_provenance": dict(self.definition_provenance),
        }