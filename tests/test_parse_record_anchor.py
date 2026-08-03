from clafact.pipeline.parse import normalize_period


def test_normalize_period_ignores_statistical_series_start_year_before_last_month():
    sentence = "지난달 건설업 취업자는 전년 동월 대비 16만9000명 감소하면서, 지난 2013년 관련 통계 작성 이래 최대 감소폭을 보였다."

    assert normalize_period(sentence, "2025-02-14") == "2025-01"
