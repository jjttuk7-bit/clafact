from clafact.kosis import build_query


def test_single_month_request_uses_start_and_end_period_without_latest_period_mode():
    query = build_query("101", "DT_MONTH", prd_de="2025-05", prd_se="M")

    assert query["startPrdDe"] == "202505"
    assert query["endPrdDe"] == "202505"
    assert "newEstPrdCnt" not in query


def test_unbounded_request_keeps_latest_period_mode():
    query = build_query("101", "DT_YEAR", prd_se="Y", recent_n=3)

    assert query["newEstPrdCnt"] == "3"
    assert "startPrdDe" not in query
