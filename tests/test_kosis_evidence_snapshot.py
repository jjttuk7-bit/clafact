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
