from clafact.kosis_evidence_autofill import autofill_from_rows


def test_autofill_translates_kosis_annual_period_code_a():
    fields = autofill_from_rows(
        table_id="DT_1B040A3",
        rows=[{"TBL_NM": "인구", "ITM_NM": "총인구", "PRD_SE": "A"}],
    )

    assert fields.time_dimension == "연"
