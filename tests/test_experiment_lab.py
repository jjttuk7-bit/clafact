from clafact.experiment_lab import run_comparison, run_mode


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

def test_each_mode_runs_independently_and_keeps_evidence():
    text = "지난해 실업률은 2.7%였다. 전화번호는 1234-5678이다."

    python_result = run_mode(text, "2025-07-14", "python", judge_fn=_judge)
    llm_result = run_mode(text, "2025-07-14", "llm", judge_fn=_judge)
    hybrid_result = run_mode(text, "2025-07-14", "hybrid", judge_fn=_judge)

    assert python_result.llm_calls == 0
    assert llm_result.llm_calls == 2
    assert hybrid_result.llm_calls == 1
    assert python_result.rows[0].candidate is True
    assert llm_result.rows[0].candidate is True
    assert "후보 판정: 통과" in python_result.rows[0].reason
    assert "적용 규칙: 수치 표현 + 변화/비교 서술" in python_result.rows[0].reason
    assert "후속 라우팅 (사실 검증 아님)" in python_result.rows[0].reason
    assert hybrid_result.rows[0].candidate is True
    assert python_result.rows[0].quantities == ["2.7%"]
    assert python_result.rows[0].parsed_period == "2024"
    assert hybrid_result.rows[1].reason == "Python 1차 후보가 아니므로 LLM 2차 판별 미호출"


def test_full_comparison_records_separate_mode_timings():
    result = run_comparison("지난해 실업률은 2.7%였다.", "2025-07-14", judge_fn=_judge)

    assert set(result.mode_results) == {"python", "llm", "hybrid"}
    assert result.elapsed_ms >= sum(mode.elapsed_ms for mode in result.mode_results.values())
