from clafact.claim_completion_store import ClaimCompletionStore


def _record(*, verdict="match"):
    return {
        "shadow_run_id": "shadow-1",
        "row_index": 1,
        "evidence_id": "DT_TEST:total",
        "snapshot_id": "kosis-1",
        "verdict": verdict,
        "snapshot": {"snapshot_id": "kosis-1", "reproducible_url": "https://kosis.kr/repro"},
    }


def test_appending_same_completed_claim_twice_keeps_one_immutable_record(tmp_path):
    record = _record()

    with ClaimCompletionStore(tmp_path / "completed.db") as store:
        assert store.append(record) is True
        assert store.append(record) is False
        assert store.list_for_run("shadow-1") == [record]


def test_rejects_a_different_payload_for_an_existing_completed_claim(tmp_path):
    with ClaimCompletionStore(tmp_path / "completed.db") as store:
        store.append(_record())

        try:
            store.append(_record(verdict="mismatch"))
        except ValueError as error:
            assert "different payload" in str(error)
        else:
            raise AssertionError("immutable completed Claim must reject a different payload")
