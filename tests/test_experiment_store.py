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
            "hcx_status": "success",
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
            store.append_run(
                {**_run(), "article_title": "덮어쓰면 안 됨"},
                _sentences(),
            )

        assert store.get_run("run-001")["article_title"] == "소비자물가 기사"
        assert len(store.get_sentences("run-001")) == 2


def test_rejects_a_run_when_declared_sentence_count_does_not_match_rows():
    with ExperimentStore(":memory:") as store:
        with pytest.raises(ValueError, match="sentence_count"):
            store.append_run({**_run(), "sentence_count": 1}, _sentences())

        assert store.get_run("run-001") is None


def test_rejects_an_unknown_disagreement_class():
    sentences = _sentences()
    sentences[0]["disagreement_class"] = "OTHER"

    with ExperimentStore(":memory:") as store:
        with pytest.raises(ValueError, match="disagreement_class"):
            store.append_run(_run(), sentences)

        assert store.get_run("run-001") is None


@pytest.mark.parametrize(
    ("hcx_status", "hcx_candidate", "disagreement_class"),
    [
        ("success", True, "P+/H-"),
        ("success", None, "HCX_ERROR"),
        ("json_error", False, "HCX_ERROR"),
        ("json_error", None, "P-/H-"),
    ],
)
def test_rejects_contradictory_hcx_status_candidate_and_class(
    hcx_status,
    hcx_candidate,
    disagreement_class,
):
    sentences = _sentences()
    sentences[0].update(
        hcx_status=hcx_status,
        hcx_candidate=hcx_candidate,
        disagreement_class=disagreement_class,
    )

    with ExperimentStore(":memory:") as store:
        with pytest.raises(ValueError, match="HCX|disagreement_class"):
            store.append_run(_run(), sentences)

        assert store.get_run("run-001") is None


def test_rolls_back_a_new_run_when_sentence_insertion_fails():
    sentences = _sentences()
    sentences[1]["sentence_index"] = sentences[0]["sentence_index"]

    with ExperimentStore(":memory:") as store:
        with pytest.raises(sqlite3.IntegrityError):
            store.append_run(_run("run-rollback"), sentences)

        assert store.get_run("run-rollback") is None


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


def test_lists_runs_with_deterministic_filters_and_pagination():
    with ExperimentStore(":memory:") as store:
        fixtures = [
            ("run-a", "2026-07-24T10:00:00+09:00", "HCX", "HCX-003", "v1"),
            ("run-b", "2026-07-25T10:00:00+09:00", "HCX", "HCX-005", "v2"),
            ("run-c", "2026-07-26T10:00:00+09:00", "GPT", "gpt-5", "v2"),
            ("run-d", "2026-07-26T10:00:00+09:00", "HCX", "HCX-005", "v2"),
        ]
        for run_id, created_at, provider, model, prompt_version in fixtures:
            store.append_run(
                {
                    **_run(run_id), "created_at": created_at, "provider": provider,
                    "model": model, "prompt_version": prompt_version,
                },
                _sentences(),
            )

        assert [row["run_id"] for row in store.list_runs(limit=2)] == ["run-d", "run-c"]
        assert [row["run_id"] for row in store.list_runs(limit=2, offset=2)] == ["run-b", "run-a"]
        assert [row["run_id"] for row in store.list_runs(
            date_from="2026-07-25", date_to="2026-07-26", provider="HCX",
            model="HCX-005", prompt_version="v2",
        )] == ["run-d", "run-b"]


def test_gets_sentences_for_selected_runs_and_filtered_aggregate():
    with ExperimentStore(":memory:") as store:
        for run_id, created_at, provider in (
            ("run-old", "2026-07-24T10:00:00+09:00", "HCX"),
            ("run-new", "2026-07-26T10:00:00+09:00", "GPT"),
        ):
            store.append_run(
                {**_run(run_id), "created_at": created_at, "provider": provider},
                _sentences(),
            )

        selected = store.get_sentences_for_runs(["run-new", "run-old"])
        filtered = store.get_filtered_sentences(
            date_from="2026-07-26", date_to="2026-07-26", provider="GPT"
        )

    assert [(row["run_id"], row["sentence_index"]) for row in selected] == [
        ("run-new", 0), ("run-new", 1), ("run-old", 0), ("run-old", 1)
    ]
    assert {row["run_id"] for row in filtered} == {"run-new"}


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (501, 0), (1, -1)])
def test_list_runs_rejects_unsafe_pagination(limit, offset):
    with ExperimentStore(":memory:") as store:
        with pytest.raises(ValueError, match="limit|offset"):
            store.list_runs(limit=limit, offset=offset)


def test_list_all_runs_pages_through_more_than_ui_batch_limit():
    with ExperimentStore(":memory:") as store:
        for index in range(501):
            store.append_run(
                {
                    **_run(f"run-{index:03d}"),
                    "created_at": f"2026-07-26T10:{index // 60:02d}:{index % 60:02d}+09:00",
                    "sentence_count": 0,
                },
                [],
            )

        runs = store.list_all_runs(provider="NAVER")

    assert len(runs) == 501
    assert runs[0]["run_id"] == "run-500"
    assert runs[-1]["run_id"] == "run-000"
