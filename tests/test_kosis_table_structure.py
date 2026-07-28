from clafact.kosis_table_structure import classify_table_structure


def test_classifies_time_series_when_period_varies_under_one_indicator():
    result = classify_table_structure([
        {"PRD_DE": "2024", "ITM_NM": "총인구", "C1_OBJ_NM": "시도", "C1_NM": "전국"},
        {"PRD_DE": "2025", "ITM_NM": "총인구", "C1_OBJ_NM": "시도", "C1_NM": "전국"},
    ])

    assert result.structure_type == "time_series"
    assert "시간" in result.reason


def test_classifies_regional_comparison_when_region_values_vary():
    result = classify_table_structure([
        {"PRD_DE": "2025", "ITM_NM": "총인구", "C1_OBJ_NM": "시도", "C1_NM": "서울"},
        {"PRD_DE": "2025", "ITM_NM": "총인구", "C1_OBJ_NM": "시도", "C1_NM": "부산"},
    ])

    assert result.structure_type == "regional_comparison"


def test_classifies_crosstab_when_two_dimensions_vary():
    result = classify_table_structure([
        {"PRD_DE": "2025", "ITM_NM": "고용률", "C1_OBJ_NM": "성별", "C1_NM": "남자", "C2_OBJ_NM": "연령", "C2_NM": "20대"},
        {"PRD_DE": "2025", "ITM_NM": "고용률", "C1_OBJ_NM": "성별", "C1_NM": "여자", "C2_OBJ_NM": "연령", "C2_NM": "30대"},
    ])

    assert result.structure_type == "crosstab"


def test_classifies_indicator_bundle_when_multiple_items_vary_without_dimensions():
    result = classify_table_structure([
        {"PRD_DE": "2025", "ITM_NM": "총인구"},
        {"PRD_DE": "2025", "ITM_NM": "세대수"},
    ])

    assert result.structure_type == "indicator_bundle"
