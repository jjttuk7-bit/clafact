from clafact.claim_profile import build_claim_profile
from clafact.kosis_candidate_search import evaluate_kosis_candidate
from clafact.kosis_semantic_card import build_semantic_card_draft, semantic_card_review_model
from clafact.pipeline.retrieve import TableHit


def test_builds_seven_axis_semantic_card_draft_from_candidate_and_claim():
    profile = build_claim_profile("2025년 3월 서울 청년층 실업률은 7.5%였다.")
    candidate = evaluate_kosis_candidate(
        "2025년 3월 서울 청년층 실업률은 7.5%였다.",
        TableHit("DT_YOUTH", "101", "서울 청년층 월별 실업률", "경제활동인구조사", 0.9),
        profile=profile,
    )

    card = build_semantic_card_draft(candidate, profile)

    assert card.table_id == "DT_YOUTH"
    assert card.topic == "고용"
    assert card.indicator == "실업률"
    assert card.target_scope == "청년층"
    assert card.spatial == "서울"
    assert card.time == "월"
    assert card.unit == "%"
    assert set(card.field_status) == {
        "topic", "indicator", "target_scope", "spatial", "time", "unit", "definition_formula"
    }
    assert card.field_status["definition_formula"] == "unconfirmed"


def test_semantic_card_review_model_exposes_seven_axes_and_claim_context():
    profile = build_claim_profile("2025년 3월 서울 청년층 실업률은 7.5%였다.")
    candidate = evaluate_kosis_candidate(
        "2025년 3월 서울 청년층 실업률은 7.5%였다.",
        TableHit("DT_YOUTH", "101", "서울 청년층 월별 실업률", "경제활동인구조사", 0.9),
        profile=profile,
    )
    model = semantic_card_review_model(build_semantic_card_draft(candidate, profile), profile)

    assert set(model["axes"]) == {
        "topic", "indicator", "target_scope", "spatial", "time", "unit", "definition_formula"
    }
    assert model["claim_context"]["region"] == "서울"
    assert model["claim_context"]["population"] == "청년층"
    assert model["is_reused"] is False
