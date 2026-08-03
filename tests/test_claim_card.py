from clafact.claim_card import build_claim_card, review_claim_card


def test_build_claim_card_combines_profile_parse_and_source_fields():
    card = build_claim_card(
        "2025년 3월 서울 청년층 실업률은 7.5%였다.",
        "2025-04-01",
    )

    assert card.topic == "고용"
    assert card.indicator == "실업률"
    assert card.period == "2025-03"
    assert card.claim_value_raw == "7.5%"
    assert card.unit == "%"
    assert card.region == "서울"
    assert card.population == "청년층"
    assert card.ready_for_kosis is True


def test_multiple_quantities_require_reviewer_to_choose_the_claim_value():
    card = build_claim_card(
        "지난달 소비자물가가 지난해 같은 달 대비 2.4% 상승하며, 9월(2.1%)에 이어 상승했다.",
        "2025-11-04",
    )

    assert card.ready_for_kosis is False
    assert any("복수 수치" in reason for reason in card.readiness_reasons)

    reviewed = review_claim_card(card, claim_value_raw="2.4%")

    assert reviewed.ready_for_kosis is True
    assert reviewed.claim_value_raw == "2.4%"
    assert reviewed.reviewed is True


def test_non_kosis_route_cannot_become_ready_after_review():
    card = build_claim_card("미국 소비자물가는 3.0% 상승했다.", "2025-11-04")

    reviewed = review_claim_card(card, claim_value_raw="3.0%", period="2025-10")

    assert reviewed.ready_for_kosis is False
    assert reviewed.readiness == "out_of_scope"


def test_claim_card_keeps_a_negative_claim_value_verbatim():
    card = build_claim_card("지난달 배추 물가는 -34.5% 하락했다.", "2025-11-04")

    assert card.claim_value_raw == "-34.5%"
    assert card.claim_value == -34.5
    assert card.normalized_value == -34.5
