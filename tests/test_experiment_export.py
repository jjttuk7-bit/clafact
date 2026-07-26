import csv
import io
import json
import os
import time

import pytest

from clafact import experiment_export as export_module
from clafact.experiment_export import export_run_csv, export_runs_csv, promote_to_golden
from clafact.experiment_store import ExperimentStore


def _stored_run(store: ExperimentStore) -> None:
    store.append_run(
        {
            "run_id": "run-001", "created_at": "2026-07-26T11:30:00+09:00",
            "article_hash": "article-hash", "article_title": "=SUM(A1:A2)",
            "article_date": "2026-07-26", "provider": "HCX", "model": "HCX-005",
            "prompt_version": "candidate-v2", "python_ms": 3, "hcx_ms": 21741,
            "total_ms": 21744, "hcx_calls": 2, "source_row_count": 1,
            "sentence_count": 2,
        },
        [
            {
                "sentence_index": 1, "sentence_hash": "sentence-hash-1",
                "sentence_text": "+위험한 스프레드시트 수식", "python_candidate": False,
                "python_reason": "@python reason", "hcx_status": "success",
                "hcx_candidate": True, "hcx_reason": "=hcx reason",
                "evidence_status": "search_required", "disagreement_class": "P-/H+",
            },
            {
                "sentence_index": 2, "sentence_hash": "sentence-hash-2",
                "sentence_text": "둘 다 탐지한 문장", "python_candidate": True,
                "python_reason": "python reason", "hcx_status": "success",
                "hcx_candidate": True, "hcx_reason": "hcx reason",
                "evidence_status": "sufficient", "disagreement_class": "P+/H+",
            },
        ],
    )


def test_exports_selected_run_as_utf8_bom_csv_with_deterministic_safe_columns():
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        store.update_review("run-001", 1, human_label="true_candidate",
                            review_note="-검토 메모", reviewed_at="2026-07-26T11:40:00+09:00")
        payload = export_run_csv(store, "run-001")

    assert payload.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    assert list(rows[0]) == [
        "run_id", "created_at", "article_hash", "article_title", "article_date",
        "provider", "model", "prompt_version", "python_ms", "hcx_ms", "total_ms",
        "hcx_calls", "source_row_count", "sentence_count", "sentence_index",
        "sentence_hash", "sentence_text", "python_candidate", "python_reason",
        "hcx_status", "hcx_candidate", "hcx_reason", "evidence_status",
        "disagreement_class", "human_label", "review_note", "reviewed_at",
    ]
    assert len(rows) == 2
    assert rows[0]["sentence_hash"] == "sentence-hash-1"
    assert rows[0]["human_label"] == "true_candidate"
    for column in ("article_title", "sentence_text", "python_reason", "hcx_reason", "review_note"):
        assert rows[0][column].startswith("'")


def test_export_rejects_an_unknown_run():
    with ExperimentStore(":memory:") as store:
        with pytest.raises(KeyError, match="run-missing"):
            export_run_csv(store, "run-missing")


def test_exports_multiple_runs_with_stable_run_metadata_and_order():
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        run_two = {
            "run_id": "run-002", "created_at": "2026-07-27T11:30:00+09:00",
            "article_hash": "article-hash-2", "article_title": "+두 번째",
            "article_date": "2026-07-27", "provider": "GPT", "model": "=gpt-5",
            "prompt_version": "candidate-v3", "python_ms": 4, "hcx_ms": 10,
            "total_ms": 14, "hcx_calls": 2, "source_row_count": 1,
            "sentence_count": 1,
        }
        store.append_run(run_two, [{
            "sentence_index": 1, "sentence_hash": "sentence-hash-3",
            "sentence_text": "두 번째 문장", "python_candidate": False,
            "python_reason": "python", "hcx_status": "success",
            "hcx_candidate": True, "hcx_reason": "hcx",
            "evidence_status": "search_required", "disagreement_class": "P-/H+",
        }])
        payload = export_runs_csv(store, ["run-001", "run-002"])

    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    assert [(row["run_id"], row["sentence_index"]) for row in rows] == [
        ("run-002", "1"), ("run-001", "1"), ("run-001", "2")
    ]
    assert rows[0]["provider"] == "GPT"
    assert rows[0]["model"] == "'=gpt-5"
    assert rows[0]["article_title"] == "'+두 번째"


def test_multiple_run_export_rejects_missing_and_empty_selection():
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        with pytest.raises(ValueError, match="하나 이상"):
            export_runs_csv(store, [])
        with pytest.raises(KeyError, match="run-missing"):
            export_runs_csv(store, ["run-001", "run-missing"])

@pytest.mark.parametrize("label", [None, "hold"])
def test_golden_promotion_rejects_unreviewed_or_held_sentences(tmp_path, label):
    golden_path = tmp_path / "goldenset" / "hybrid_disagreements_v0.jsonl"
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        if label is not None:
            store.update_review("run-001", 1, human_label=label, review_note="더 확인",
                                reviewed_at="2026-07-26T11:40:00+09:00")
        with pytest.raises(ValueError, match="true_candidate 또는 false_positive"):
            promote_to_golden(store, "run-001", 1, golden_path)
    assert not golden_path.exists()


@pytest.mark.parametrize("label", ["true_candidate", "false_positive"])
def test_explicit_promotion_appends_only_reviewed_decisions_with_provenance(tmp_path, label):
    golden_path = tmp_path / "goldenset" / "hybrid_disagreements_v0.jsonl"
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        store.update_review("run-001", 1, human_label=label, review_note="사람 검토 완료",
                            reviewed_at="2026-07-26T11:40:00+09:00")
        promoted = promote_to_golden(store, "run-001", 1, golden_path)

    stored = json.loads(golden_path.read_text(encoding="utf-8").strip())
    assert stored == promoted
    assert stored == {
        "sentence_hash": "sentence-hash-1", "sentence_text": "+위험한 스프레드시트 수식",
        "disagreement_class": "P-/H+", "human_label": label,
        "python_reason": "@python reason", "hcx_reason": "=hcx reason",
        "evidence_status": "search_required", "provider": "HCX", "model": "HCX-005",
        "prompt_version": "candidate-v2", "reviewed_at": "2026-07-26T11:40:00+09:00",
        "source_run_id": "run-001", "source_sentence_index": 1,
    }


def test_golden_promotion_rejects_duplicate_hash_without_overwriting(tmp_path):
    golden_path = tmp_path / "goldenset" / "hybrid_disagreements_v0.jsonl"
    golden_path.parent.mkdir(parents=True)
    original = '{"sentence_hash":"sentence-hash-1","sentinel":"keep"}\n'
    golden_path.write_text(original, encoding="utf-8")
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        store.update_review("run-001", 1, human_label="true_candidate", review_note=None,
                            reviewed_at="2026-07-26T11:40:00+09:00")
        with pytest.raises(ValueError, match="이미 골든셋"):
            promote_to_golden(store, "run-001", 1, golden_path)
    assert golden_path.read_text(encoding="utf-8") == original

def _stored_class(store: ExperimentStore, disagreement_class: str) -> None:
    configs = {
        "P+/H+": (True, "success", True),
        "P+/H-": (True, "success", False),
        "P-/H-": (False, "success", False),
        "HCX_ERROR": (True, "parse_error", None),
    }
    python_candidate, hcx_status, hcx_candidate = configs[disagreement_class]
    store.append_run(
        {
            "run_id": "run-denied", "created_at": "2026-07-26T11:30:00+09:00",
            "article_hash": "article-denied", "article_title": "denied",
            "article_date": "2026-07-26", "provider": "HCX", "model": "HCX-005",
            "prompt_version": "candidate-v2", "python_ms": 1, "hcx_ms": 2,
            "total_ms": 3, "hcx_calls": 1, "source_row_count": 1, "sentence_count": 1,
        },
        [{
            "sentence_index": 1, "sentence_hash": f"hash-{disagreement_class}",
            "sentence_text": f"{disagreement_class} 문장", "python_candidate": python_candidate,
            "python_reason": "python", "hcx_status": hcx_status,
            "hcx_candidate": hcx_candidate, "hcx_reason": "hcx",
            "evidence_status": None, "disagreement_class": disagreement_class,
        }],
    )
    store.update_review(
        "run-denied", 1, human_label="true_candidate", review_note="검토 완료",
        reviewed_at="2026-07-26T11:40:00+09:00",
    )


@pytest.mark.parametrize("disagreement_class", ["P+/H+", "P-/H-", "HCX_ERROR"])
def test_golden_promotion_rejects_non_disagreement_classes(tmp_path, disagreement_class):
    golden_path = tmp_path / "hybrid_disagreements_v0.jsonl"
    with ExperimentStore(":memory:") as store:
        _stored_class(store, disagreement_class)
        with pytest.raises(ValueError, match="P\\+/H- 또는 P-/H\\+"):
            promote_to_golden(store, "run-denied", 1, golden_path)
    assert not golden_path.exists()


def test_atomic_promotion_preserves_original_and_releases_lock_when_replace_fails(tmp_path, monkeypatch):
    golden_path = tmp_path / "hybrid_disagreements_v0.jsonl"
    original = '{"sentence_hash":"existing","order":1}\n'
    golden_path.write_text(original, encoding="utf-8")
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        store.update_review("run-001", 1, human_label="true_candidate", review_note=None,
                            reviewed_at="2026-07-26T11:40:00+09:00")
        monkeypatch.setattr(os, "replace",
                            lambda source, target: (_ for _ in ()).throw(OSError("replace failed")))
        with pytest.raises(OSError, match="replace failed"):
            promote_to_golden(store, "run-001", 1, golden_path)

    assert golden_path.read_text(encoding="utf-8") == original
    with export_module._exclusive_file_lock(golden_path):
        pass
    assert list(tmp_path.glob(f".{golden_path.name}.*.tmp")) == []


def test_concurrent_promotions_write_one_line_and_reject_the_duplicate(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading

    database_path = tmp_path / "research.db"
    golden_path = tmp_path / "hybrid_disagreements_v0.jsonl"
    # A non-trivial existing file widens the old check-then-append race without changing semantics.
    original_rows = [json.dumps({"sentence_hash": f"existing-{index}"}) for index in range(20000)]
    golden_path.write_text("\n".join(original_rows) + "\n", encoding="utf-8")
    with ExperimentStore(database_path) as store:
        _stored_run(store)
        store.update_review("run-001", 1, human_label="true_candidate", review_note=None,
                            reviewed_at="2026-07-26T11:40:00+09:00")

    start = threading.Barrier(2)

    def promote_once():
        with ExperimentStore(database_path) as thread_store:
            start.wait()
            try:
                promote_to_golden(thread_store, "run-001", 1, golden_path)
                return "created"
            except ValueError as error:
                assert "이미 골든셋" in str(error)
                return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: promote_once(), range(2)))

    rows = [json.loads(line) for line in golden_path.read_text(encoding="utf-8").splitlines()]
    assert sorted(outcomes) == ["created", "duplicate"]
    assert sum(row.get("sentence_hash") == "sentence-hash-1" for row in rows) == 1
    assert [row["sentence_hash"] for row in rows[:3]] == ["existing-0", "existing-1", "existing-2"]

def test_p_plus_h_minus_reviewed_sentence_can_be_promoted(tmp_path):
    golden_path = tmp_path / "hybrid_disagreements_v0.jsonl"
    with ExperimentStore(":memory:") as store:
        _stored_class(store, "P+/H-")
        promoted = promote_to_golden(store, "run-denied", 1, golden_path)
    assert promoted["disagreement_class"] == "P+/H-"

def test_dead_owner_lock_is_reclaimed_before_promotion(tmp_path):
    golden_path = tmp_path / "hybrid_disagreements_v0.jsonl"
    lock_path = golden_path.with_name(golden_path.name + ".lock")
    lock_path.write_text(
        json.dumps({"token": "dead-owner", "pid": 999_999_999, "created_at": time.time()}),
        encoding="utf-8",
    )
    with ExperimentStore(":memory:") as store:
        _stored_run(store)
        store.update_review("run-001", 1, human_label="true_candidate", review_note=None,
                            reviewed_at="2026-07-26T11:40:00+09:00")
        promoted = promote_to_golden(store, "run-001", 1, golden_path)

    assert promoted["sentence_hash"] == "sentence-hash-1"
    replacement_metadata = json.loads(lock_path.read_text(encoding="utf-8"))
    assert replacement_metadata["token"] != "dead-owner"
    assert replacement_metadata["pid"] == os.getpid()


def test_live_current_lock_is_not_stolen(tmp_path, monkeypatch):
    golden_path = tmp_path / "hybrid_disagreements_v0.jsonl"
    lock_path = golden_path.with_name(golden_path.name + ".lock")
    monkeypatch.setattr(export_module, "_LOCK_RETRIES", 2)
    monkeypatch.setattr(export_module, "_LOCK_RETRY_SECONDS", 0)

    with export_module._exclusive_file_lock(golden_path):
        with ExperimentStore(":memory:") as store:
            _stored_run(store)
            store.update_review("run-001", 1, human_label="true_candidate", review_note=None,
                                reviewed_at="2026-07-26T11:40:00+09:00")
            with pytest.raises(TimeoutError, match="잠금을 획득하지 못했습니다"):
                promote_to_golden(store, "run-001", 1, golden_path)

    metadata = json.loads(lock_path.read_text(encoding="utf-8"))
    assert metadata["token"]
    assert metadata["pid"] == os.getpid()
    assert metadata["created_at"] <= time.time()
    assert not golden_path.exists()
