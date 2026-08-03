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


def test_store_lists_candidate_searches_for_one_shadow_run(tmp_path):
    with KosisCandidateRunStore(tmp_path / "runs.db") as store:
        store.append(
            shadow_run_id="shadow-1", row_index=2, sentence="문장", query="물가",
            candidates=[], created_at="2026-07-29T10:00:00+09:00",
        )
        store.append(
            shadow_run_id="shadow-2", row_index=1, sentence="다른 문장", query="인구",
            candidates=[], created_at="2026-07-29T11:00:00+09:00",
        )
        searches = store.list_for_shadow_run("shadow-1")

    assert len(searches) == 1
    assert searches[0]["row_index"] == 2

def test_candidate_history_distinguishes_atomic_claims_in_one_sentence(tmp_path):
    with KosisCandidateRunStore(tmp_path / "runs.db") as store:
        store.append(
            shadow_run_id="shadow-1", row_index=11, claim_index=1, sentence="문장", query="물가",
            candidates=[], created_at="2026-08-04T10:00:00+09:00",
        )
        store.append(
            shadow_run_id="shadow-1", row_index=11, claim_index=2, sentence="문장", query="물가",
            candidates=[], created_at="2026-08-04T10:01:00+09:00",
        )
        searches = store.list_for_shadow_run("shadow-1")

    assert [search["claim_index"] for search in searches] == [2, 1]
