import csv
import io
import json

import pytest

from clafact.experiment_export import export_run_csv, promote_to_golden
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
