from clafact.claim_card import build_claim_card, review_claim_card
from clafact.claim_card_store import ClaimCardStore


def _confirmed_card():
    draft = build_claim_card("2025년 3월 서울 청년층 실업률은 7.5%였다.", "2025-04-01")
    return review_claim_card(draft, confirmed_at="2026-08-03T22:00:00+09:00")


def test_store_persists_and_reuses_confirmed_card_for_same_shadow_row(tmp_path):
    card = _confirmed_card()
    with ClaimCardStore(tmp_path / "cards.db") as store:
        assert store.upsert("run-1", 4, card) is True
        stored = store.get("run-1", 4)
        assert store.upsert("run-1", 4, card) is False

    assert stored is not None
    assert stored["indicator"] == "실업률"
    assert stored["confirmed_at"] == "2026-08-03T22:00:00+09:00"


def test_store_rejects_unconfirmed_card(tmp_path):
    card = build_claim_card("2025년 3월 서울 청년층 실업률은 7.5%였다.", "2025-04-01")
    with ClaimCardStore(tmp_path / "cards.db") as store:
        try:
            store.upsert("run-1", 4, card)
        except ValueError as error:
            assert "confirmed" in str(error)
        else:
            raise AssertionError("unconfirmed Claim Card must not be persisted")
