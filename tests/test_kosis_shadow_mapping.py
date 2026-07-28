from clafact.kosis_shadow_mapping import KosisShadowMapping


def test_mapping_preserves_sentence_table_and_human_note():
    mapping = KosisShadowMapping(
        shadow_run_id="shadow-001", row_index=3, table_id="DT_1B040A3",
        source_selection={"시도": "전국"}, note="인구 지표 후보 근거", status="candidate",
    )

    assert mapping.as_dict()["shadow_run_id"] == "shadow-001"
    assert mapping.as_dict()["source_selection"]["시도"] == "전국"
