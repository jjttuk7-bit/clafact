from clafact.experiment_input import clean_uploaded_article_body


def test_uploaded_article_body_stops_before_related_articles_and_profiles():
    raw = (
        "입력 2025.11.04. 10:00 소비자물가는 2.4% 상승했다. "
        "관련 기사 다른 뉴스는 7% 상승했다. "
        "김승현 기자 약력 구독"
    )

    cleaned = clean_uploaded_article_body(raw)

    assert cleaned == "소비자물가는 2.4% 상승했다."
    assert "관련 기사" not in cleaned
    assert "다른 뉴스" not in cleaned
    assert "김승현 기자" not in cleaned


def test_uploaded_article_body_rejects_body_that_becomes_empty_after_boundary_cut():
    raw = "입력 2025.11.04. 10:00 관련 기사 다른 뉴스"

    assert clean_uploaded_article_body(raw) == ""
