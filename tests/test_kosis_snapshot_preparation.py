import pytest

from clafact.kosis_snapshot_preparation import prepare_kosis_snapshot_context


def test_preparation_assembles_autofill_structure_and_reproducible_snapshot_context():
    row = {
        "TBL_NM": "월별 소비자물가 등락률",
        "ORG_NM": "국가데이터처",
        "ITM_NM": "전년동월비(%)",
        "C1_OBJ_NM": "지수종류",
        "C1_NM": "총지수",
        "PRD_SE": "M",
        "UNIT_NM": "%",
        "PRD_DE": "2026.06",
        "DT": "2.0",
    }

    result = prepare_kosis_snapshot_context(
        table_id="DT_CPI",
        org_id="101",
        rows=[row],
        retrieved_at="2026-07-29T10:00:00+09:00",
    )

    assert result.fields.indicator == "전년동월비(%)"
    assert result.fields.source_selection == "지수종류=총지수"
    assert result.structure.structure_type == "unknown"
    assert result.snapshot_context.org_id == "101"
    assert result.snapshot_context.table_id == "DT_CPI"
    assert result.snapshot_context.query_params == {"recent_n": 1}
    assert result.snapshot_context.rows == (row,)
    assert result.snapshot_context.as_dict() == {
        "org_id": "101",
        "table_id": "DT_CPI",
        "query_params": {"recent_n": 1},
        "retrieved_at": "2026-07-29T10:00:00+09:00",
        "rows": [row],
    }


def test_preparation_keeps_nested_snapshot_context_immutable():
    result = prepare_kosis_snapshot_context(
        table_id="DT_CPI",
        org_id="101",
        rows=[{"TBL_NM": "소비자물가", "ITM_NM": "전년동월비", "DT": "2.0"}],
        retrieved_at="2026-07-29T10:00:00+09:00",
    )

    with pytest.raises(TypeError):
        result.snapshot_context.query_params["recent_n"] = 2
    with pytest.raises(TypeError):
        result.snapshot_context.rows[0]["DT"] = "3.0"