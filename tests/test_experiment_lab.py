from clafact.experiment_lab import run_comparison


def _judge(sentence: str) -> tuple[bool, str]:
    if "전화번호" in sentence:
        return False, "연락처는 통계 주장이 아닙니다"
    return True, "공식 통계로 대조 가능한 주장입니다"


def test_comparison_keeps_three_independent_detection_results():
    result = run_comparison(
        "지난해 실업률은 2.7%였다. 전화번호는 1234-5678이다.",
        "2025-07-14",
        judge_fn=_judge,
    )

    assert len(result.rows) == 2
    claim, noise = result.rows
    assert claim.python_candidate is True
    assert claim.llm_verifiable is True
    assert claim.hybrid_candidate is True
    assert claim.parsed_period == "2024"
    assert noise.python_candidate is False
    assert noise.llm_verifiable is False
    assert noise.hybrid_candidate is False
    assert result.llm_calls == 3  # LLM 단독 2회 + Python 후보의 하이브리드 1회


def test_hybrid_preserves_python_candidate_when_llm_call_fails():
    def unavailable(_sentence: str) -> tuple[bool, str]:
        raise RuntimeError("HCX unavailable")

    result = run_comparison("지난해 실업률은 2.7%였다.", "2025-07-14", judge_fn=unavailable)

    row = result.rows[0]
    assert row.python_candidate is True
    assert row.llm_verifiable is None
    assert row.hybrid_candidate is True
    assert "보수적 유지" in row.hybrid_reason
