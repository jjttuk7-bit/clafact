"""운영 파이프라인을 변경하지 않고 Shadow Lab 실험 행을 생성한다."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from clafact.experiment_modes import run_comparison
from clafact.experiment_types import Judge
from clafact.shadow_policy import ShadowPolicy


@dataclass(frozen=True)
class ShadowExperimentResult:
    """저장 전 단계의 연구 전용 실행 결과."""

    rows: list[dict[str, Any]]
    llm_calls: int
    elapsed_ms: int
    disagreement_counts: dict[str, int]


def _risk_reasons(row: Any) -> tuple[str, ...]:
    risks: list[str] = []
    if row.hcx_status != "success":
        risks.append("llm_error")
    elif row.python_candidate != row.llm_verifiable:
        risks.append("candidate_conflict")
    if row.python_candidate and not row.quantities:
        risks.append("required_slot_missing")
    if row.python_candidate and not row.parsed_period:
        risks.append("ambiguous_time_or_unit")
    return tuple(risks)


def run_shadow_experiment(
    text: str,
    article_date: str,
    policy: ShadowPolicy,
    *,
    judge_fn: Judge | None = None,
) -> ShadowExperimentResult:
    """기존 비교 엔진의 결과를 연구·검토용 중립 레코드로 변환한다.

    이 함수는 운영 저장소와 판정 결과를 전혀 변경하지 않는다.
    """
    comparison = run_comparison(text, article_date, judge_fn)
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(comparison.rows, start=1):
        risks = _risk_reasons(row)
        review_state = "needs_review" if risks else "auto"
        rows.append({
            "row_index": index,
            "sentence": row.sentence,
            "baseline": {
                "python_candidate": row.python_candidate,
                "reason": "기존 Python 규칙 탐지 결과",
            },
            "shadow": {
                "llm_candidate": row.llm_verifiable,
                "llm_reason": row.llm_reason,
                "hybrid_candidate": row.hybrid_candidate,
                "hybrid_reason": row.hybrid_reason,
                "hcx_status": row.hcx_status,
                "disagreement_class": row.disagreement_class,
                "claim_type": row.claim_type,
                "route": row.route,
                "quantities": row.quantities,
                "parsed_period": row.parsed_period,
                "policy_version": policy.version,
            },
            "risk_reasons": risks,
            "review_state": review_state,
        })
    return ShadowExperimentResult(
        rows=rows,
        llm_calls=comparison.llm_calls,
        elapsed_ms=comparison.elapsed_ms,
        disagreement_counts=comparison.disagreement_counts,
    )
