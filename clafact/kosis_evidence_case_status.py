"""Guide a team through one complete, traceable KOSIS evidence-object case."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class KosisEvidenceCaseStatus:
    completed_steps: int
    total_steps: int
    steps: tuple[tuple[str, bool], ...]
    next_action: str


def build_evidence_case_status(
    *,
    evidence: Mapping[str, Any],
    snapshot_count: int,
    mapping_count: int,
    pending_review_count: int,
) -> KosisEvidenceCaseStatus:
    """Return a human-readable end-to-end status for one evidence object."""
    evidence_saved = bool(evidence.get("table_id"))
    snapshot_saved = bool(evidence.get("snapshot_id")) or snapshot_count > 0
    shadow_mapped = mapping_count > 0
    revision_checked = shadow_mapped and pending_review_count == 0
    steps = (
        ("근거 객체 저장", evidence_saved),
        ("조회 스냅샷 보존", snapshot_saved),
        ("Shadow 문장 연결", shadow_mapped),
        ("개정 검토 확인", revision_checked),
    )
    completed_steps = sum(done for _, done in steps)
    if not snapshot_saved:
        next_action = "KOSIS API 자동 채우기 후 근거 객체를 다시 저장해 조회 스냅샷을 남기세요."
    elif not shadow_mapped:
        next_action = "Shadow 문장을 이 근거 객체에 연결하세요."
    elif pending_review_count:
        next_action = "대기 중인 KOSIS 개정 검토를 결정하세요."
    else:
        next_action = "첫 실제 근거 객체 사례가 완성되었습니다."
    return KosisEvidenceCaseStatus(
        completed_steps=completed_steps,
        total_steps=len(steps),
        steps=steps,
        next_action=next_action,
    )
