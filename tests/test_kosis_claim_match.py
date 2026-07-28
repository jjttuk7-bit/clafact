from clafact.kosis_claim_match import evaluate_claim_evidence_match
from clafact.kosis_evidence import KosisEvidenceObject


def evidence() -> KosisEvidenceObject:
    return KosisEvidenceObject(
        table_id="DT_1B040A3",
        url="https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B040A3",
        title="주민등록인구",
        organization="통계청",
        indicator="주민등록인구",
        dimensions=("시도", "성별"),
        time_dimension="연",
        unit="명",
        definition="",
        source_selection={"시도": "전국", "성별": "계"},
        retrieved_at="2026-07-28T00:00:00+09:00",
    )


def test_scores_indicator_unit_time_and_explicit_region_match():
    result = evaluate_claim_evidence_match(
        "2025년 전국 주민등록인구는 5,000만 명이다.",
        evidence(),
    )

    assert result.score == 100
    assert result.status == "high"
    assert "단위 일치" in result.reasons


def test_flags_unit_conflict_without_claiming_factual_error():
    result = evaluate_claim_evidence_match(
        "2025년 전국 주민등록인구는 3.1%다.",
        evidence(),
    )

    assert result.score < 100
    assert result.status == "needs_review"
    assert "단위 충돌" in result.reasons
