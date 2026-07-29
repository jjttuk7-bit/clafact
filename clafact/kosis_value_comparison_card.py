"""Read-only view models for KOSIS value comparison results."""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from clafact.kosis_value_comparison import KosisValueComparison


def _normalize_period(value: object) -> str:
    period = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})[.-](\d{1,2})", period)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
    return period.replace(".", "-")


def _compact(value: object) -> str:
    return re.sub(r"[\s()_%]", "", str(value or "")).lower()


def _normalized_unit(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return {"퍼센트": "%", "퍼센트포인트": "%p"}.get(normalized, normalized)


def _claim_unit(value: str) -> str:
    compact = value.strip().lower()
    if compact.endswith("%p"):
        return "%p"
    if compact.endswith("%"):
        return "%"
    return ""


def _selection_matches(record: Mapping[str, object], expected: Mapping[str, str]) -> bool:
    selection = record.get("selection") or {}
    if not isinstance(selection, Mapping):
        return False
    return all(
        not value or str(selection.get(dimension, "")).strip() == str(value).strip()
        for dimension, value in expected.items()
    )


@dataclass(frozen=True)
class KosisValueCandidate:
    """One read-only official-value candidate displayed by the comparison card."""

    period: str
    indicator: str
    selection: Mapping[str, str]
    value: str
    unit: str
    official_value: str
    match_score: int
    gate_matches: tuple[tuple[str, bool], ...]


@dataclass(frozen=True)
class KosisValueComparisonCard:
    """Read-only card model; it never changes comparison or snapshot state."""

    status: str
    reason: str
    claim_value: str
    official_value: str
    claim_period: str
    official_period: str
    snapshot_id: str
    snapshot_retrieved_at: str
    gate_results: tuple[Mapping[str, object], ...]
    primary: KosisValueCandidate | None
    alternatives: tuple[KosisValueCandidate, ...]


def _candidate(
    record: Mapping[str, object],
    *,
    comparison: KosisValueComparison,
    evidence_indicator: str,
    evidence_selection: Mapping[str, str],
) -> KosisValueCandidate:
    period = _normalize_period(record.get("period"))
    indicator = str(record.get("indicator", "")).strip()
    value = str(record.get("value", "")).strip()
    unit = str(record.get("unit", "")).strip()
    selection = record.get("selection") or {}
    selection_copy = {
        str(dimension): str(selected)
        for dimension, selected in selection.items()
    } if isinstance(selection, Mapping) else {}
    gate_matches = (
        ("기간", period == _normalize_period(comparison.claim_period)),
        ("지표", _compact(indicator) == _compact(evidence_indicator)),
        ("선택 조건", _selection_matches(record, evidence_selection)),
        ("단위", _normalized_unit(unit) == _claim_unit(comparison.claim_value)),
    )
    return KosisValueCandidate(
        period=period,
        indicator=indicator,
        selection=MappingProxyType(selection_copy),
        value=value,
        unit=unit,
        official_value=f"{value}{unit}",
        match_score=sum(passed for _, passed in gate_matches),
        gate_matches=gate_matches,
    )


def _is_primary(candidate: KosisValueCandidate, comparison: KosisValueComparison) -> bool:
    return (
        comparison.status in {"match", "mismatch"}
        and candidate.period == _normalize_period(comparison.official_period)
        and candidate.official_value == comparison.official_value
        and all(passed for _, passed in candidate.gate_matches)
    )


def _candidate_order(candidate: KosisValueCandidate) -> tuple[object, ...]:
    matches = tuple(int(passed) for _, passed in candidate.gate_matches)
    selection = tuple(sorted((str(key), str(value)) for key, value in candidate.selection.items()))
    return (
        *(-matched for matched in matches),
        candidate.period,
        _compact(candidate.indicator),
        selection,
        candidate.value,
        _normalized_unit(candidate.unit),
    )


def build_value_comparison_card(
    comparison: KosisValueComparison,
    snapshot: Mapping[str, object] | None,
    *,
    evidence_indicator: str,
    evidence_selection: Mapping[str, str],
) -> KosisValueComparisonCard:
    """Create a deterministic, read-only display model from existing research data."""
    records = (snapshot or {}).get("records") or []
    candidates = [
        _candidate(
            record,
            comparison=comparison,
            evidence_indicator=evidence_indicator,
            evidence_selection=evidence_selection,
        )
        for record in records
        if isinstance(record, Mapping)
    ]
    primary_index = next(
        (index for index, candidate in enumerate(candidates) if _is_primary(candidate, comparison)),
        None,
    )
    primary = candidates[primary_index] if primary_index is not None else None
    alternatives = [
        candidate for index, candidate in enumerate(candidates)
        if index != primary_index
    ]
    alternatives.sort(key=_candidate_order)
    return KosisValueComparisonCard(
        status=comparison.status,
        reason=comparison.reason,
        claim_value=comparison.claim_value,
        official_value=comparison.official_value,
        claim_period=comparison.claim_period,
        official_period=comparison.official_period,
        snapshot_id=comparison.snapshot_id,
        snapshot_retrieved_at=comparison.snapshot_retrieved_at,
        gate_results=tuple(MappingProxyType(dict(gate)) for gate in comparison.gate_results),
        primary=primary,
        alternatives=tuple(alternatives),
    )