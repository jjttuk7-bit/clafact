from clafact.kosis_candidate_run_store import KosisCandidateRunStore


def test_store_keeps_candidate_run_and_flattens_csv_rows(tmp_path):
    with KosisCandidateRunStore(tmp_path / "runs.db") as store:
        run_id = store.append(
            shadow_run_id="shadow-1",
            row_index=2,
            sentence="소비자물가가 2.4% 상승했다.",
            query="소비자물가",
            candidates=[
                {"rank": 1, "table_id": "DT_MONTH", "title": "월별 소비자물가 등락률", "score": 100, "reasons": ["지표 일치"], "penalties": []},
            ],
            created_at="2026-07-28T23:00:00+09:00",
        )

        rows = store.list_csv_rows()

    assert run_id
    assert rows[0]["shadow_run_id"] == "shadow-1"
    assert rows[0]["table_id"] == "DT_MONTH"
    assert rows[0]["reasons"] == "지표 일치"
