from clafact.coordinate_verdict_flow import build_coordinate_verdict


def test_coordinate_verdict_builds_evidence_snapshot_mapping_and_match():
    result = build_coordinate_verdict(
        shadow_run_id="run-1", row_index=1, claim_sentence="2025년 10월 배추 물가는 전년동월비 -34.5%였다.", article_date="2025-11-04",
        org_id="101", table_id="DT_TEST", title="월별 물가", indicator="전년동월비", unit="%",
        selection={"품목": "배추"}, rows=[{
            "C1_OBJ_NM":"품목", "C1_NM":"배추", "ITM_NM":"전년동월비", "UNIT_NM":"%",
            "PRD_DE":"202510", "DT":"-34.5", "LST_CHN_DE":"2025-11-01"
        }], retrieved_at="2025-11-04T00:00:00+09:00", query_params={"prd_de":"202510"},
    )

    assert result.evidence.source_selection == {"품목": "배추"}
    assert result.snapshot.records[0]["value"] == "-34.5"
    assert result.mapping.status == "reviewed"
    assert result.comparison.status == "match"
