"""Pure presentation helpers for persisted verification-lab history."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


DISAGREEMENT_ORDER = ("P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR")


@dataclass(frozen=True, slots=True)
class HistorySummary:
    run_count: int
    sentence_count: int
    counts: dict[str, int]


def build_history_summary(
    runs: Sequence[Mapping[str, Any]],
    sentences: Sequence[Mapping[str, Any]],
) -> HistorySummary:
    """Count outcomes across runs without making cross-version accuracy claims."""
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
    return HistorySummary(
        run_count=len(selected_run_ids),
        sentence_count=sentence_count,
        counts=counts,
    )


def distinct_filter_values(
    runs: Sequence[Mapping[str, Any]], field: str
) -> tuple[str, ...]:
    return tuple(sorted({str(run.get(field) or "") for run in runs} - {""}))
