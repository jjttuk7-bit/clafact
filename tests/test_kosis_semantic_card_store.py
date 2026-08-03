from clafact.kosis_semantic_card import SemanticCard
from clafact.kosis_semantic_card_store import KosisSemanticCardStore


def _confirmed_card(title: str = "서울 청년층 월별 실업률") -> SemanticCard:
    return SemanticCard(
        table_id="DT_YOUTH", org_id="101", table_name=title,
        topic="고용", indicator="실업률", target_scope="청년층", spatial="서울",
        time="월", unit="%", definition_formula="", field_status={"topic": "confirmed"},
        tag_source="reviewed", semantic_confidence=1.0, confirmed_at="2026-08-03T10:00:00+09:00",
    )


def test_store_persists_and_reuses_confirmed_card_by_table_id(tmp_path):
    with KosisSemanticCardStore(tmp_path / "cards.db") as store:
        assert store.upsert(_confirmed_card()) is True
        stored = store.get("DT_YOUTH")
        assert store.upsert(_confirmed_card("수정된 제목")) is False

    assert stored is not None
    assert stored["target_scope"] == "청년층"
    assert stored["spatial"] == "서울"


def test_store_rejects_unconfirmed_draft(tmp_path):
    draft = _confirmed_card()
    draft = SemanticCard(**{**draft.__dict__, "confirmed_at": ""})
    with KosisSemanticCardStore(tmp_path / "cards.db") as store:
        try:
            store.upsert(draft)
        except ValueError as error:
            assert "confirmed" in str(error)
        else:
            raise AssertionError("unconfirmed draft must not be persisted")
