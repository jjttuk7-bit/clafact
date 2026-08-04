from clafact.kosis_coordinate_selection import (
    extract_coordinate_axes,
    matching_rows,
    recommend_coordinate_selection,
)


def rows():
    return [
        {"C1_OBJ_NM": "품목", "C1_NM": "배추", "ITM_NM": "전년동월비", "PRD_DE": "202510", "UNIT_NM": "%", "DT": "-34.5"},
        {"C1_OBJ_NM": "품목", "C1_NM": "무", "ITM_NM": "전년동월비", "PRD_DE": "202510", "UNIT_NM": "%", "DT": "-40.5"},
    ]


def test_coordinate_axes_and_recommendation_preserve_real_kosis_row_values():
    axes = extract_coordinate_axes(rows())
    selection = recommend_coordinate_selection(
        axes, subject="배추", period="2025-10", unit="%", comparison="전년동월비"
    )

    assert axes["품목"] == ("배추", "무")
    assert selection == {"품목": "배추", "항목": "전년동월비", "시점": "202510", "단위": "%"}
    selected = matching_rows(rows(), selection)
    assert len(selected) == 1
    assert selected[0]["DT"] == "-34.5"
