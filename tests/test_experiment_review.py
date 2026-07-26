import inspect

import pytest

from clafact import experiment_review
from clafact.experiment_review import (
    pop_review_feedback,
    promote_reviewed_sentence,
    reviewable_sentences,
    save_human_review,
    store_review_feedback,
)
from clafact.experiment_store import ExperimentStore


def _seed_run(database_path):
    with ExperimentStore(database_path) as store:
        store.append_run(
            {
                "run_id": "review-run", "created_at": "2026-07-26T12:00:00+09:00",
                "article_hash": "article", "article_title": "title",
                "article_date": "2026-07-26", "provider": "HCX", "model": "HCX-005",
                "prompt_version": "candidate-v2", "python_ms": 1, "hcx_ms": 2,
                "total_ms": 3, "hcx_calls": 2, "source_row_count": 1, "sentence_count": 2,
            },
            [
                {
                    "sentence_index": 1, "sentence_hash": "semantic-hash",
                    "sentence_text": "Python만 탐지", "python_candidate": True,
                    "python_reason": "python", "hcx_status": "success",
                    "hcx_candidate": False, "hcx_reason": "hcx",
                    "evidence_status": "search_required", "disagreement_class": "P+/H-",
                },
                {
                    "sentence_index": 2, "sentence_hash": "agreement-hash",
                    "sentence_text": "둘 다 탐지", "python_candidate": True,
                    "python_reason": "python", "hcx_status": "success",
                    "hcx_candidate": True, "hcx_reason": "hcx",
                    "evidence_status": "sufficient", "disagreement_class": "P+/H+",
                },
            ],
        )


def test_review_handler_persists_decision_and_feedback_survives_one_rerun(tmp_path):
    database_path = tmp_path / "verification_lab.db"
    _seed_run(database_path)

    message = save_human_review(
        database_path, "review-run", 1,
        human_label="true_candidate", review_note="  핵심 사례  ",
        reviewed_at="2026-07-26T12:10:00+09:00",
    )
    session_state = {}
    store_review_feedback(session_state, message)

    with ExperimentStore(database_path) as store:
        reviewed = store.get_sentences("review-run")[0]
    assert reviewed["human_label"] == "true_candidate"
    assert reviewed["review_note"] == "핵심 사례"
    assert reviewed["reviewed_at"] == "2026-07-26T12:10:00+09:00"
    assert pop_review_feedback(session_state) == message
    assert pop_review_feedback(session_state) == ""
    assert "clafact.service.store" not in inspect.getsource(experiment_review)


def test_review_list_contains_only_semantic_disagreements(tmp_path):
    database_path = tmp_path / "verification_lab.db"
    _seed_run(database_path)
    with ExperimentStore(database_path) as store:
        rows = store.get_sentences("review-run")

    assert [row["sentence_index"] for row in reviewable_sentences(rows)] == [1]


def test_promotion_handler_keeps_backend_eligibility_guard(tmp_path):
    database_path = tmp_path / "verification_lab.db"
    golden_path = tmp_path / "hybrid_disagreements_v0.jsonl"
    _seed_run(database_path)
    for sentence_index in (1, 2):
        save_human_review(
            database_path, "review-run", sentence_index,
            human_label="true_candidate", review_note=None,
            reviewed_at="2026-07-26T12:10:00+09:00",
        )

    promoted = promote_reviewed_sentence(database_path, "review-run", 1, golden_path)
    assert promoted["disagreement_class"] == "P+/H-"
    with pytest.raises(ValueError, match="P\\+/H- 또는 P-/H\\+"):
        promote_reviewed_sentence(database_path, "review-run", 2, golden_path)
