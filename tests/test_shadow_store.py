import pytest

from clafact.shadow_store import ShadowStore


def _run(run_id: str = "shadow-1") -> dict:
    return {
        "run_id": run_id,
        "created_at": "2026-07-28T10:00:00+09:00",
        "input_hash": "input-hash",
        "policy_json": "{}",
        "baseline_name": "python",
        "shadow_name": "hcx_hybrid",
        "status": "completed",
        "summary_json": "{}",
    }


def _row(sentence: str = "인구는 감소했다.") -> dict:
    return {
        "row_index": 1,
        "sentence": sentence,
        "baseline_json": "{}",
        "shadow_json": "{}",
        "review_state": "needs_review",
        "risk_reasons_json": '["candidate_conflict"]',
    }


def test_store_persists_reviewable_row(tmp_path):
    with ShadowStore(tmp_path / "shadow_lab.db") as store:
        assert store.append_run(_run(), [_row()]) is True

        assert store.get_run("shadow-1")["status"] == "completed"
        assert store.list_review_rows("shadow-1")[0]["sentence"] == "인구는 감소했다."


def test_store_rejects_different_payload_for_existing_run_id(tmp_path):
    with ShadowStore(tmp_path / "shadow_lab.db") as store:
        store.append_run(_run(), [_row()])

        with pytest.raises(ValueError, match="different payload"):
            store.append_run(_run(), [_row("다른 문장")])


def test_store_appends_review_and_marks_row_reviewed(tmp_path):
    with ShadowStore(tmp_path / "shadow_lab.db") as store:
        store.append_run(_run(), [_row()])

        assert store.append_review(
            "shadow-1", 1, action="hold", note="기간 확인 필요", reviewed_at="2026-07-28T10:01:00+09:00"
        ) is True
        assert store.list_review_rows("shadow-1")[0]["review_state"] == "reviewed"


def test_store_lists_runs_newest_first(tmp_path):
    with ShadowStore(tmp_path / "shadow_lab.db") as store:
        store.append_run(_run("shadow-old"), [_row()])
        newest = _run("shadow-new")
        newest["created_at"] = "2026-07-28T11:00:00+09:00"
        store.append_run(newest, [_row()])

        assert [row["run_id"] for row in store.list_runs(limit=5)] == ["shadow-new", "shadow-old"]