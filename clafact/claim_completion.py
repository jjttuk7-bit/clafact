"""Create one reproducible Claim-to-KOSIS completion record."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from clafact.kosis_evidence_snapshot import build_evidence_snapshot
from clafact.kosis_value_comparison import KosisValueComparison, compare_claim_to_snapshot


@dataclass(frozen=True)
class CompletedClaim:
    """A self-contained result for one sentence, one KOSIS evidence selection, and one snapshot."""

    claim_id: str
    sentence: str
    article_date: str
    table_id: str
    source_url: str
    evidence_indicator: str
    evidence_selection: Mapping[str, str]
    snapshot_id: str
    snapshot: Mapping[str, object]
    comparison: KosisValueComparison

    @property
    def verdict(self) -> str:
        return {
            "match": "match",
            "mismatch": "mismatch",
        }.get(self.comparison.status, "hold")

    def as_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "sentence": self.sentence,
            "article_date": self.article_date,
            "evidence": {
                "table_id": self.table_id,
                "source_url": str(self.snapshot["reproducible_url"]),
                "indicator": self.evidence_indicator,
                "selection": dict(self.evidence_selection),
            },
            "snapshot_id": self.snapshot_id,
            "snapshot": dict(self.snapshot),
            "verdict": self.verdict,
            "comparison": self.comparison.as_dict(),
        }


def complete_claim_case(
    *,
    claim_id: str,
    sentence: str,
    article_date: str,
    org_id: str,
    table_id: str,
    query_params: Mapping[str, object],
    rows: Sequence[Mapping[str, object]],
    evidence_indicator: str,
    evidence_selection: Mapping[str, str],
    source_url: str,
    retrieved_at: str,
) -> CompletedClaim:
    """Build a snapshot and verdict without guessing missing KOSIS conditions."""
    snapshot = build_evidence_snapshot(
        org_id=org_id,
        table_id=table_id,
        query_params=query_params,
        retrieved_at=retrieved_at,
        rows=rows,
    )
    comparison = compare_claim_to_snapshot(
        claim_sentence=sentence,
        article_date=article_date,
        evidence_indicator=evidence_indicator,
        evidence_selection=evidence_selection,
        snapshot=snapshot.as_dict(),
    )
    return CompletedClaim(
        claim_id=claim_id,
        sentence=sentence,
        article_date=article_date,
        table_id=table_id,
        source_url=snapshot.reproducible_url,
        evidence_indicator=evidence_indicator,
        evidence_selection=dict(evidence_selection),
        snapshot_id=snapshot.snapshot_id,
        snapshot=snapshot.as_dict(),
        comparison=comparison,
    )


def complete_selected_claim(
    *,
    shadow_run_id: str,
    row_index: int,
    sentence: str,
    mapping: Mapping[str, object],
    comparison: Mapping[str, object],
    snapshot: Mapping[str, object],
) -> dict[str, object]:
    """Freeze a user-selected persisted evidence result without refetching KOSIS."""
    evidence_id = str(mapping.get("evidence_id") or mapping.get("table_id") or "").strip()
    table_id = str(mapping.get("table_id") or "").strip()
    snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
    source_url = str(snapshot.get("reproducible_url") or "").strip()
    comparison_snapshot_id = str(comparison.get("snapshot_id") or "").strip()
    snapshot_table_id = str(snapshot.get("table_id") or "").strip()
    if not shadow_run_id.strip() or row_index < 0 or not sentence.strip():
        raise ValueError("selected Shadow sentence is required")
    if not evidence_id or not table_id:
        raise ValueError("selected KOSIS evidence is required")
    if not snapshot_id or not source_url:
        raise ValueError("selected KOSIS snapshot is required")
    if comparison_snapshot_id and comparison_snapshot_id != snapshot_id:
        raise ValueError("comparison snapshot does not match selected snapshot")
    if snapshot_table_id and snapshot_table_id != table_id:
        raise ValueError("selected snapshot table does not match selected evidence table")
    status = str(comparison.get("status") or "")
    verdict = status if status in {"match", "mismatch"} else "hold"
    return {
        "shadow_run_id": shadow_run_id,
        "row_index": row_index,
        "sentence": sentence,
        "evidence_id": evidence_id,
        "snapshot_id": snapshot_id,
        "verdict": verdict,
        "evidence": {
            "table_id": table_id,
            "source_url": source_url,
            "indicator": mapping.get("indicator", ""),
            "selection": dict(mapping.get("source_selection", {})),
        },
        "comparison": dict(comparison),
        "snapshot": dict(snapshot),
    }