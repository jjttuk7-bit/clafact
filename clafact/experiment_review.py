"""Small research-only handlers for verification-lab human review flows."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from clafact.experiment_export import promote_to_golden
from clafact.experiment_store import ExperimentStore


REVIEWABLE_DISAGREEMENTS = frozenset({"P+/H-", "P-/H+"})
REVIEW_FEEDBACK_KEY = "experiment_lab_research_feedback"
REVIEW_SAVED_MESSAGE = "사람 검토를 연구 전용 이력에 저장했습니다."


def reviewable_sentences(sentences: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Keep only semantic Python/HCX disagreements for human review."""
    return [
        sentence
        for sentence in sentences
        if sentence.get("disagreement_class") in REVIEWABLE_DISAGREEMENTS
    ]


def save_human_review(
    database_path: str | Path,
    run_id: str,
    sentence_index: int,
    *,
    human_label: str,
    review_note: str | None,
    reviewed_at: str,
) -> str:
    """Persist one decision in the research database, never the operating store."""
    normalized_note = review_note.strip() if review_note else None
    with ExperimentStore(database_path) as research_store:
        research_store.update_review(
            run_id,
            sentence_index,
            human_label=human_label,
            review_note=normalized_note or None,
            reviewed_at=reviewed_at,
        )
    return REVIEW_SAVED_MESSAGE


def promote_reviewed_sentence(
    database_path: str | Path,
    run_id: str,
    sentence_index: int,
    golden_path: str | Path,
) -> dict[str, Any]:
    """Promote through the backend eligibility and atomic-write guard."""
    with ExperimentStore(database_path) as research_store:
        return promote_to_golden(
            research_store,
            run_id,
            sentence_index,
            golden_path,
        )


def store_review_feedback(session_state: MutableMapping[str, Any], message: str) -> None:
    session_state[REVIEW_FEEDBACK_KEY] = message


def pop_review_feedback(session_state: MutableMapping[str, Any]) -> str:
    return str(session_state.pop(REVIEW_FEEDBACK_KEY, ""))
