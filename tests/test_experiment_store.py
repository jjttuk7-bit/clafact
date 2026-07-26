import sqlite3

import pytest

from clafact.experiment_store import ExperimentStore


def _run(run_id: str = "run-001") -> dict:
    return {
        "run_id": run_id,
        "created_at": "2026-07-26T12:00:00+09:00",
        "article_hash": "article-sha256",
        "article_title": "소비자물가 기사",
        "article_date": "2025-11-04",
        "provider": "NAVER",
        "model": "HCX-005",
        "prompt_version": "candidate-v2",
        "python_ms": 3,
        "hcx_ms": 21_741,
        "total_ms": 21_744,
        "hcx_calls": 14,
        "source_row_count": 1,
        "sentence_count": 2,
    }


def _sentences() -> list[dict]:
    return [
        {
            "sentence_index": 0,
            "sentence_hash": "sentence-0-sha256",
            "sentence_text": "소비자물가는 전년보다 2.4% 올랐다.",
            "python_candidate": True,
            "python_reason": "수치와 비교 표현",
            "hcx_status": "ok",
            "hcx_candidate": True,
            "hcx_reason": "수치 주장",
            "evidence_status": "search_required",
            "disagreement_class": "P+/H+",
        },
        {
            "sentence_index": 1,
            "sentence_hash": "sentence-1-sha256",
            "sentence_text": "HCX 응답 파싱에 실패했다.",
            "python_candidate": False,
            "python_reason": "수치 없음",
            "hcx_status": "json_error",
            "hcx_candidate": None,
            "hcx_reason": "JSON 응답 없음",
            "evidence_status": "unavailable",
            "disagreement_class": "HCX_ERROR",
        },
    ]


def test_appends_and_reads_a_run_with_its_sentence_rows():
    with ExperimentStore(":memory:") as store:
        store.append_run(_run(), _sentences())

        saved_run = store.get_run("run-001")
        saved_sentences = store.get_sentences("run-001")

    assert saved_run == _run()
    assert saved_sentences == [
        {**_sentences()[0], "run_id": "run-001", "human_label": None, "review_note": None, "reviewed_at": None},
        {**_sentences()[1], "run_id": "run-001", "human_label": None, "review_note": None, "reviewed_at": None},
    ]
    assert saved_sentences[1]["disagreement_class"] == "HCX_ERROR"
    assert saved_sentences[1]["hcx_candidate"] is None


def test_duplicate_run_id_is_rejected_without_overwriting_existing_rows():
    with ExperimentStore(":memory:") as store:
        store.append_run(_run(), _sentences())

        with pytest.raises(sqlite3.IntegrityError):
            store.append_run({**_run(), "article_title": "덮어쓰면 안 됨"}, [])

        assert store.get_run("run-001")["article_title"] == "소비자물가 기사"
        assert len(store.get_sentences("run-001")) == 2


@pytest.mark.parametrize("label", ["true_candidate", "false_positive", "hold"])
def test_updates_a_sentence_review_with_an_allowed_label(label):
    with ExperimentStore(":memory:") as store:
        store.append_run(_run(), _sentences())

        store.update_review(
            "run-001",
            0,
            human_label=label,
            review_note="사람 검토",
            reviewed_at="2026-07-26T12:30:00+09:00",
        )

        reviewed = store.get_sentences("run-001")[0]

    assert reviewed["human_label"] == label
    assert reviewed["review_note"] == "사람 검토"
    assert reviewed["reviewed_at"] == "2026-07-26T12:30:00+09:00"


def test_rejects_an_unknown_review_label():
    with ExperimentStore(":memory:") as store:
        store.append_run(_run(), _sentences())

        with pytest.raises(ValueError, match="human_label"):
            store.update_review(
                "run-001",
                0,
                human_label="approved",
                review_note=None,
                reviewed_at="2026-07-26T12:30:00+09:00",
            )


def test_file_backed_store_initializes_parent_directory(tmp_path):
    database = tmp_path / "research" / "verification_lab.db"

    with ExperimentStore(database) as store:
        store.append_run(_run(), _sentences())

    with ExperimentStore(database) as reopened:
        assert reopened.get_run("run-001")["model"] == "HCX-005"
