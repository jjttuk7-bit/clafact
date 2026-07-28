from clafact.kosis_candidate_search import evaluate_kosis_candidate, suggest_kosis_candidates
from clafact.pipeline.retrieve import TableHit


def test_monthly_year_over_year_rate_is_ranked_above_annual_index():
    sentence = "지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승했다."
    monthly_rate = evaluate_kosis_candidate(
        sentence,
        TableHit("DT_MONTHLY_RATE", "101", "월별 소비자물가 등락률(전년동월비)", "소비자물가조사", 0.2),
    )
    annual_index = evaluate_kosis_candidate(
        sentence,
        TableHit("DT_ANNUAL_INDEX", "101", "소비자물가지수(2020=100)", "소비자물가조사", 1.0),
    )

    assert monthly_rate.score > annual_index.score
    assert "월 단위 일치" in monthly_rate.reasons
    assert "전년동월비 일치" in monthly_rate.reasons
    assert "등락률/증감률 단위 일치" in monthly_rate.reasons
    assert "전년동월비 표현 없음" in annual_index.penalties


def test_search_results_are_ranked_and_limited_to_top_three():
    class FakeIndex:
        def search(self, query: str, top_k: int):
            assert query == "소비자물가"
            assert top_k == 10
            return [
                TableHit("ANNUAL", "101", "연도별 소비자물가지수", "소비자물가조사", 1.0),
                TableHit("MONTHLY", "101", "월별 소비자물가 등락률(전년동월비)", "소비자물가조사", 0.2),
                TableHit("SECOND", "101", "월별 소비자물가 등락률", "소비자물가조사", 0.5),
                TableHit("THIRD", "101", "소비자물가지수", "소비자물가조사", 0.7),
            ]

    candidates = suggest_kosis_candidates(
        "지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승했다.",
        FakeIndex(),
    )

    assert [candidate.hit.tbl_id for candidate in candidates] == ["MONTHLY", "SECOND", "ANNUAL"]

def test_official_item_metadata_penalizes_month_over_month_for_year_over_year_claim():
    sentence = "지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승했다."
    result = evaluate_kosis_candidate(
        sentence,
        TableHit("DT_MONTH", "101", "월별 소비자물가 등락률", "소비자물가조사", 1.0),
        item_names=("전월비",),
    )

    assert "공식 항목 전월비 불일치" in result.penalties
    assert result.score < 90


def test_candidate_selects_year_over_year_item_within_same_table():
    result = evaluate_kosis_candidate(
        "지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승했다.",
        TableHit("DT_MONTH", "101", "월별 소비자물가 등락률", "소비자물가조사", 1.0),
        item_names=("전월비", "전년비"),
    )
    assert result.selected_item == "전년비"


def test_candidate_exposes_point_by_point_score_breakdown():
    result = evaluate_kosis_candidate(
        "지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승했다.",
        TableHit("DT_MONTH", "101", "월별 소비자물가 등락률(전년동월비)", "소비자물가조사", 1.0),
        item_names=("전년동월비(%)",),
    )

    assert "+50 지표 일치" in result.score_breakdown
    assert "+20 공식 항목 전년동월비 일치" in result.score_breakdown