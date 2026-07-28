"""Shadow analysis sentence and KOSIS evidence research mapping."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


VALID_MAPPING_STATUSES = frozenset({"candidate", "reviewed", "rejected"})


@dataclass(frozen=True)
class KosisShadowMapping:
    """Connect one Shadow result sentence to one KOSIS evidence object."""

    shadow_run_id: str
    row_index: int
    table_id: str
    source_selection: Mapping[str, str]
    note: str
    status: str
    match_score: int | None = None
    match_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.shadow_run_id.strip():
            raise ValueError("shadow_run_id is required")
        if self.row_index < 0:
            raise ValueError("row_index must be non-negative")
        if not self.table_id.strip():
            raise ValueError("table_id is required")
        if self.status not in VALID_MAPPING_STATUSES:
            raise ValueError("status must be candidate, reviewed, or rejected")
        if self.match_score is not None and not 0 <= self.match_score <= 100:
            raise ValueError("match_score must be between 0 and 100")

    def as_dict(self) -> dict[str, object]:
        return {
            "shadow_run_id": self.shadow_run_id,
            "row_index": self.row_index,
            "table_id": self.table_id,
            "source_selection": dict(self.source_selection),
            "note": self.note,
            "status": self.status,
            "match_score": self.match_score,
            "match_reasons": list(self.match_reasons),
        }