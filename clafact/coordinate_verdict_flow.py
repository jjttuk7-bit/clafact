"""Build the complete research record set for one confirmed KOSIS coordinate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from clafact.kosis_claim_match import evaluate_claim_evidence_match
from clafact.kosis_evidence import KosisEvidenceObject
from clafact.kosis_evidence_input import build_manual_evidence
from clafact.kosis_evidence_snapshot import KosisEvidenceSnapshot, build_evidence_snapshot
from clafact.kosis_shadow_mapping import KosisShadowMapping
from clafact.kosis_value_comparison import KosisValueComparison, compare_claim_to_snapshot


@dataclass(frozen=True)
class CoordinateVerdict:
    evidence: KosisEvidenceObject
    snapshot: KosisEvidenceSnapshot
    mapping: KosisShadowMapping
    comparison: KosisValueComparison


def build_coordinate_verdict(*, shadow_run_id: str, row_index: int, claim_sentence: str, article_date: str,
                            org_id: str, table_id: str, title: str, indicator: str, unit: str,
                            selection: Mapping[str, str], rows: Sequence[Mapping[str, object]],
                            retrieved_at: str, query_params: Mapping[str, object]) -> CoordinateVerdict:
    """Create all immutable records for a human-confirmed exact KOSIS coordinate."""
    evidence = build_manual_evidence(
        table_id=table_id, url=f"https://kosis.kr/statHtml/statHtml.do?orgId={org_id}&tblId={table_id}",
        title=title, organization="국가데이터처", indicator=indicator,
        dimensions=", ".join(selection), time_dimension="수록시점", unit=unit,
        definition="", source_selection=";".join(f"{key}={value}" for key, value in selection.items()),
        retrieved_at=retrieved_at,
    )
    snapshot = build_evidence_snapshot(org_id=org_id, table_id=table_id, query_params=query_params,
                                       retrieved_at=retrieved_at, rows=rows)
    match = evaluate_claim_evidence_match(claim_sentence, evidence)
    mapping = KosisShadowMapping(
        shadow_run_id=shadow_run_id, row_index=row_index, table_id=table_id,
        evidence_id=evidence.evidence_id, source_selection=selection, note="확정 좌표 기반 자동 연결",
        status="reviewed", match_score=match.score, match_reasons=match.reasons,
        match_score_breakdown=match.score_breakdown,
    )
    comparison = compare_claim_to_snapshot(
        claim_sentence=claim_sentence, article_date=article_date, evidence_indicator=indicator,
        evidence_selection=selection, snapshot=snapshot.as_dict(),
    )
    return CoordinateVerdict(evidence=evidence, snapshot=snapshot, mapping=mapping, comparison=comparison)
