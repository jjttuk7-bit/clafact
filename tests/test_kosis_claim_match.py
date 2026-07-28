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


def test_matches_year_over_year_rate_semantically_and_explains_each_point():
    year_over_year_evidence = KosisEvidenceObject(
        table_id="DT_1J22042", url="https://kosis.kr/table", title="월별 소비자물가 등락률",
        organization="통계청", indicator="전년동월비(%)", dimensions=("지수종류",),
        time_dimension="월", unit="%", definition="", source_selection={"지수종류": "총지수"},
        retrieved_at="2026-07-29T07:00:00+09:00",
    )

    result = evaluate_claim_evidence_match(
        "지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승했다.",
        year_over_year_evidence,
    )

    assert result.score == 85
    assert result.status == "high"
    assert any(item.startswith("+40 지표 의미 일치") for item in result.score_breakdown)
    assert "+25 단위 일치 (%)" in result.score_breakdown
    assert "+20 시간 주기 일치 (월)" in result.score_breakdown