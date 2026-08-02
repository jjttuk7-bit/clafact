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
                "source_url": self.source_url,
                "indicator": self.evidence_indicator,
                "selection": dict(self.evidence_selection),
            },
            "snapshot_id": self.snapshot_id,
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
        source_url=source_url,
        evidence_indicator=evidence_indicator,
        evidence_selection=dict(evidence_selection),
        snapshot_id=snapshot.snapshot_id,
        comparison=comparison,
    )
