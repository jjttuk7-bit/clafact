"""Find research mappings that should be revisited after a KOSIS revision."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class KosisRevisionImpact:
    shadow_run_id: str
    row_index: int
    table_id: str
    period: str
    indicator: str
    value_before: str
    value_after: str
    match_score: int | None
    note: str


def _selection_matches(
    mapping_selection: Mapping[str, object], revised_selection: Mapping[str, object]
) -> bool:
    return bool(mapping_selection) and all(
        str(revised_selection.get(key, "")) == str(value)
        for key, value in mapping_selection.items()
    )


def find_revision_impacts(
    *,
    mappings: Sequence[Mapping[str, Any]],
    comparison_rows: Sequence[Mapping[str, Any]],
) -> tuple[KosisRevisionImpact, ...]:
    """Return only mapped sentences whose selected KOSIS record was changed or removed."""
    impacts: list[KosisRevisionImpact] = []
    for comparison in comparison_rows:
        if comparison.get("change_type") not in {"changed", "removed"}:
            continue
        revised_selection = comparison.get("selection", {})
        for mapping in mappings:
            if not _selection_matches(mapping.get("source_selection", {}), revised_selection):
                continue
            impacts.append(KosisRevisionImpact(
                shadow_run_id=str(mapping["shadow_run_id"]),
                row_index=int(mapping["row_index"]),
                table_id=str(mapping["table_id"]),
                period=str(comparison.get("period", "")),
                indicator=str(comparison.get("indicator", "")),
                value_before=str(comparison.get("value_before", "")),
                value_after=str(comparison.get("value_after", "")),
                match_score=mapping.get("match_score"),
                note=str(mapping.get("note", "")),
            ))
    return tuple(impacts)
