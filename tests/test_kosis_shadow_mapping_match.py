from clafact.kosis_shadow_mapping import KosisShadowMapping


def test_mapping_preserves_applicability_score_and_reasons():
    mapping = KosisShadowMapping(
        shadow_run_id="shadow-001",
        row_index=3,
        table_id="DT_1B040A3",
        source_selection={"시도": "전국"},
        note="인구 지표 후보 근거",
        status="candidate",
        match_score=100,
        match_reasons=("지표명 일치", "단위 일치"),
    )

    assert mapping.as_dict()["match_score"] == 100
    assert mapping.as_dict()["match_reasons"] == ["지표명 일치", "단위 일치"]
