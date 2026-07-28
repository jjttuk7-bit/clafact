from clafact.kosis_shadow_mapping import KosisShadowMapping


def test_mapping_preserves_sentence_table_and_human_note():
    mapping = KosisShadowMapping(
        shadow_run_id="shadow-001", row_index=3, table_id="DT_1B040A3",
        source_selection={"시도": "전국"}, note="인구 지표 후보 근거", status="candidate",
    )

    assert mapping.as_dict()["shadow_run_id"] == "shadow-001"
    assert mapping.as_dict()["source_selection"]["시도"] == "전국"


def test_mapping_preserves_score_breakdown_for_reproducible_review():
    mapping = KosisShadowMapping(
        shadow_run_id="shadow-001", row_index=1, table_id="DT_1J22042",
        evidence_id="DT_1J22042:year", source_selection={}, note="", status="candidate",
        match_score=85, match_score_breakdown=("+40 지표 의미 일치 (전년동월비)", "+25 단위 일치 (%)"),
    )

    assert mapping.as_dict()["match_score_breakdown"] == [
        "+40 지표 의미 일치 (전년동월비)", "+25 단위 일치 (%)"
    ]