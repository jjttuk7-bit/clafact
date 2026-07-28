from clafact.pipeline.detect_llm import HcxDecision
from clafact.shadow_policy import ShadowPolicy
from clafact.shadow_runner import run_shadow_experiment


def test_shadow_runner_converts_comparison_to_research_rows():
    result = run_shadow_experiment(
        "2025년 인구는 5,000만 명이다.",
        "2026-07-28",
        ShadowPolicy.default(),
        judge_fn=lambda _: HcxDecision(False, "수치 검증 문장이 아닙니다", "unknown", "", []),
    )

    assert len(result.rows) == 1
    row = result.rows[0]
    assert row["baseline"]["python_candidate"] is True
    assert row["shadow"]["llm_candidate"] is False
    assert "candidate_conflict" in row["risk_reasons"]
    assert row["review_state"] == "needs_review"
    assert result.llm_calls >= 1


def test_shadow_runner_marks_llm_failure_for_review():
    result = run_shadow_experiment(
        "2025년 인구는 5,000만 명이다.",
        "2026-07-28",
        ShadowPolicy.default(),
        judge_fn=lambda _: None,
    )

    row = result.rows[0]
    assert "llm_error" in row["risk_reasons"]
    assert row["review_state"] == "needs_review"
