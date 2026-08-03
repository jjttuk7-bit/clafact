from clafact.kosis_evidence_snapshot import build_evidence_snapshot


def test_snapshot_preserves_reproducible_request_values_and_revision():
    snapshot = build_evidence_snapshot(
        org_id="101",
        table_id="DT_1B040A3",
        query_params={"recent_n": 1, "itm_id": "ALL"},
        retrieved_at="2026-07-28T10:00:00+09:00",
        rows=[{
            "PRD_DE": "2025", "DT": "50000000", "UNIT_NM": "명",
            "ITM_NM": "총인구", "LST_CHN_DE": "2026-06-30",
            "C1_OBJ_NM": "시도", "C1_NM": "전국",
        }],
    )

    assert snapshot.reproducible_url.startswith("https://kosis.kr/openapi/")
    assert snapshot.records[0]["value"] == "50000000"
    assert snapshot.records[0]["last_changed_at"] == "2026-06-30"
    assert len(snapshot.content_hash) == 64


def test_snapshot_preserves_dimension_codes_with_selection_labels():
    snapshot = build_evidence_snapshot(
        org_id="101", table_id="DT_X", query_params={}, retrieved_at="2026-08-03",
        rows=[{
            "PRD_DE": "2025-05", "DT": "109.67", "ITM_ID": "T", "ITM_NM": "소비자물가지수",
            "C1": "T10", "C1_OBJ_NM": "시도별", "C1_NM": "전국",
            "C2": "B01A01402", "C2_OBJ_NM": "품목별", "C2_NM": "분유",
        }],
    )

    assert snapshot.records[0]["selection_codes"] == {"C1": "T10", "C2": "B01A01402"}
    assert snapshot.records[0]["indicator_code"] == "T"
