from clafact.kosis_revision_impact import find_revision_impacts


def test_finds_mapping_that_matches_revised_selection():
    impacts = find_revision_impacts(
        mappings=[{
            "shadow_run_id": "shadow-001", "row_index": 3, "table_id": "DT_1B040A3",
            "source_selection": {"시도": "전국"}, "note": "인구 근거", "match_score": 100,
        }],
        comparison_rows=[{
            "change_type": "changed", "period": "2025", "indicator": "총인구",
            "selection": {"시도": "전국"}, "value_before": "50000000", "value_after": "50001000",
        }],
    )

    assert len(impacts) == 1
    assert impacts[0].shadow_run_id == "shadow-001"
    assert impacts[0].value_after == "50001000"


def test_does_not_flag_mapping_with_different_selection():
    impacts = find_revision_impacts(
        mappings=[{
            "shadow_run_id": "shadow-001", "row_index": 3, "table_id": "DT_1B040A3",
            "source_selection": {"시도": "서울"}, "note": "", "match_score": 70,
        }],
        comparison_rows=[{
            "change_type": "changed", "period": "2025", "indicator": "총인구",
            "selection": {"시도": "전국"}, "value_before": "50000000", "value_after": "50001000",
        }],
    )

    assert impacts == ()
