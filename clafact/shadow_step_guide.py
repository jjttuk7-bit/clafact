"""Derive a non-mutating five-step guide for Shadow Mode research."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ShadowGuideStep:
    step_id: str
    label: str
    state: str
    detail: str


@dataclass(frozen=True)
class ShadowGuideScreenHint:
    step_id: str
    message: str


@dataclass(frozen=True)
class ShadowStepGuide:
    steps: tuple[ShadowGuideStep, ...]
    completed_count: int
    next_step_id: str | None
    screen_hint: ShadowGuideScreenHint | None


def guide_next_action_text(step_id: str | None) -> str:
    """Return one concise action prompt for the first unfinished research step."""
    prompts = {
        "execute": "다음 할 일: 기사 본문을 입력하고 Shadow 실행을 시작하세요.",
        "select_sentence": "다음 할 일: 검토할 수치 주장 문장을 선택하세요.",
        "find_candidate": "다음 할 일: 선택 문장의 KOSIS 후보를 찾아보세요.",
        "compare_value": "다음 할 일: KOSIS 근거를 연결하고 실제 값 대조를 실행하세요.",
        "review_export": "다음 할 일: 검토 메모를 저장하고 연구 기록을 다운로드하세요.",
    }
    return prompts.get(step_id, "5단계 연구 기록이 준비되었습니다. 필요하면 CSV를 다운로드하세요.")

def guide_screen_hint(step_id: str | None) -> ShadowGuideScreenHint | None:
    """Describe the existing on-screen control for the current guide step."""
    hints = {
        "execute": "Shadow 실행 버튼을 눌러 연구용 분석 기록을 만드세요.",
        "select_sentence": "검토할 Shadow 문장을 선택하세요.",
        "find_candidate": "KOSIS 후보 3개 찾기 버튼을 눌러 근거 후보를 찾으세요.",
        "compare_value": "KOSIS 근거 연결 뒤 실제 값 대조를 실행하세요.",
        "review_export": "Shadow 검토 저장 후 JSON 또는 CSV를 다운로드하세요.",
    }
    return ShadowGuideScreenHint(step_id, hints[step_id]) if step_id in hints else None

def _has_row(records: Sequence[Mapping[str, Any]], row_index: int | None) -> bool:
    return row_index is not None and any(int(record.get("row_index", -1)) == row_index for record in records)


def _comparison_state(
    comparisons: Sequence[Mapping[str, Any]], row_index: int | None,
) -> str:
    selected = [
        str(comparison.get("status", ""))
        for comparison in comparisons
        if row_index is not None and int(comparison.get("row_index", -1)) == row_index
    ]
    if any(status in {"match", "mismatch"} for status in selected):
        return "complete"
    if "not_comparable" in selected:
        return "review_needed"
    return "next"


def build_shadow_step_guide(
    *,
    shadow_run: Mapping[str, Any] | None = None,
    selected_row_index: int | None = None,
    candidate_search_done: bool = False,
    mappings: Sequence[Mapping[str, Any]] = (),
    comparisons: Sequence[Mapping[str, Any]] = (),
    reviews: Sequence[Mapping[str, Any]] = (),
) -> ShadowStepGuide:
    """Return workflow guidance from existing research records, without writes."""
    has_run = bool(shadow_run and shadow_run.get("rows"))
    has_selection = has_run and selected_row_index is not None
    has_mapping = _has_row(mappings, selected_row_index)
    has_candidate_step = has_mapping or candidate_search_done
    comparison_state = _comparison_state(comparisons, selected_row_index) if has_mapping else "next"
    has_review = _has_row(reviews, selected_row_index)

    states = {
        "execute": "complete" if has_run else "next",
        "select_sentence": "complete" if has_selection else ("locked" if not has_run else "next"),
        "find_candidate": "complete" if has_candidate_step else ("locked" if not has_selection else "next"),
        "compare_value": (
            comparison_state if has_mapping else ("locked" if not has_candidate_step else "next")
        ),
        "review_export": "complete" if has_review else (
            "locked" if comparison_state != "complete" else "next"
        ),
    }
    details = {
        "execute": "기사 본문과 발행일을 입력한 뒤 Shadow 실행을 만듭니다.",
        "select_sentence": "검토할 수치 주장 문장을 한 개 고릅니다.",
        "find_candidate": "선택 문장에 맞는 KOSIS 후보를 찾거나 수동 근거를 준비합니다.",
        "compare_value": "근거를 연결하고 저장된 KOSIS 스냅샷의 실제 값과 대조합니다.",
        "review_export": "검토 메모를 저장한 뒤 JSON 또는 CSV로 연구 기록을 내보냅니다.",
    }
    labels = {
        "execute": "Shadow 실행",
        "select_sentence": "문장 선택",
        "find_candidate": "KOSIS 후보 탐색",
        "compare_value": "근거 연결·실제 값 대조",
        "review_export": "검토·내보내기",
    }
    ordered_ids = tuple(labels)
    steps = tuple(
        ShadowGuideStep(step_id=step_id, label=labels[step_id], state=states[step_id], detail=details[step_id])
        for step_id in ordered_ids
    )
    completed_count = sum(step.state == "complete" for step in steps)
    next_step_id = next(
        (step.step_id for step in steps if step.state in {"next", "review_needed"}),
        None,
    )
    return ShadowStepGuide(
        steps=steps,
        completed_count=completed_count,
        next_step_id=next_step_id,
        screen_hint=guide_screen_hint(next_step_id),
    )
