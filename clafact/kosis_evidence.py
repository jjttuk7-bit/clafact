"""KOSIS 통계표를 추적 가능한 연구 근거 객체로 표현한다."""
from __future__ import annotations

from dataclasses import dataclass
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

    def __post_init__(self) -> None:
        for field in ("table_id", "url", "title", "organization", "indicator", "retrieved_at"):
            if not getattr(self, field).strip():
                raise ValueError(f"{field} is required")

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
        }
