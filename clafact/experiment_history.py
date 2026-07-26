"""Pure controller and presentation helpers for persisted lab history."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


DISAGREEMENT_ORDER = ("P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR")


@dataclass(frozen=True, slots=True)
class HistorySummary:
    run_count: int
    sentence_count: int
    counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class HistoryFilters:
    date_from: str | None = None
    date_to: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    revision: int = 0

    def as_kwargs(self) -> dict[str, str | None]:
        return {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
        }


@dataclass(frozen=True, slots=True)
class PreparedHistoryExport:
    signature: str
    payload: bytes
    row_count: int


@dataclass(frozen=True, slots=True)
class HistoryActionTarget:
    run_id: str
    sentence_index: int


def filter_signature(filters: HistoryFilters) -> str:
    signature_values = {**filters.as_kwargs(), "revision": filters.revision}
    payload = json.dumps(
        signature_values, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prepared_export_for_filters(
    prepared: PreparedHistoryExport | None,
    filters: HistoryFilters,
) -> PreparedHistoryExport | None:
    if (
        not isinstance(prepared, PreparedHistoryExport)
        or prepared.signature != filter_signature(filters)
    ):
        return None
    return prepared


def build_history_page(
    *, total_runs: int, requested_page: int, page_size: int = 50
) -> dict[str, Any]:
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    page_count = max(1, (max(0, total_runs) + page_size - 1) // page_size)
    page = min(max(1, requested_page), page_count)
    return {
        "page": page,
        "page_count": page_count,
        "offset": (page - 1) * page_size,
    }


def build_history_action_target(run_id: str, sentence_index: int) -> HistoryActionTarget:
    if not run_id:
        raise ValueError("run_id is required")
    if sentence_index < 0:
        raise ValueError("sentence_index must be non-negative")
    return HistoryActionTarget(run_id=str(run_id), sentence_index=int(sentence_index))


def build_history_summary(
    runs: Sequence[Mapping[str, Any]],
    sentences: Sequence[Mapping[str, Any]],
) -> HistorySummary:
    """Count outcomes for already selected rows without accuracy claims."""
    selected_run_ids = {str(run["run_id"]) for run in runs}
    counts = {outcome: 0 for outcome in DISAGREEMENT_ORDER}
    sentence_count = 0
    for sentence in sentences:
        if str(sentence.get("run_id")) not in selected_run_ids:
            continue
        outcome = sentence.get("disagreement_class")
        if outcome in counts:
            counts[outcome] += 1
            sentence_count += 1
    return HistorySummary(len(selected_run_ids), sentence_count, counts)


def distinct_filter_values(
    runs: Sequence[Mapping[str, Any]], field: str
) -> tuple[str, ...]:
    return tuple(sorted({str(run.get(field) or "") for run in runs} - {""}))
