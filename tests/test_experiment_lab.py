from typing import get_args

import pytest

from clafact import experiment_lab
from clafact.experiment_analysis import HCX_ERROR
from clafact.experiment_lab import run_comparison, run_mode
from clafact.pipeline.detect_llm import HcxDecision


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
    assert row.hcx_status == "call_error"
    assert row.disagreement_class == HCX_ERROR
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


def test_hcx_mode_preserves_candidate_and_evidence_status_separately():
    sentence = "이같은 물가 상승률은 지난해 7월(2.6%) 이후 15개월만에 가장 높은 수치다."

    def judge(_sentence: str):
        return HcxDecision(
            candidate=True,
            candidate_reason="수치와 비교 기간이 있는 후보 주장",
            evidence_status="needs_retrieval",
            evidence_reason="기사 내부의 직접 통계 근거는 부족함",
            quoted_spans=["지난해 7월(2.6%) 이후 15개월만에 가장 높은 수치"],
        )

    result = run_mode(sentence, "2025-11-04", "llm", judge_fn=judge)

    row = result.rows[0]
    assert row.candidate is True
    assert row.evidence_status == "needs_retrieval"
    assert row.evidence_reason == "기사 내부의 직접 통계 근거는 부족함"
    assert row.quoted_spans == ["지난해 7월(2.6%) 이후 15개월만에 가장 높은 수치"]

@pytest.mark.parametrize(
    ("sentence", "hcx_candidate", "expected"),
    [
        ("물가는 지난해보다 2.4% 올랐다.", True, "P+/H+"),
        ("물가는 지난해보다 2.4% 올랐다.", False, "P+/H-"),
        ("먹거리 물가는 여전히 오름세를 보였다.", True, "P-/H+"),
        ("먹거리 물가는 여전히 오름세를 보였다.", False, "P-/H-"),
    ],
)
def test_full_comparison_classifies_all_success_combinations(
    sentence: str,
    hcx_candidate: bool,
    expected: str,
) -> None:
    def judge(_sentence: str) -> tuple[bool, str]:
        return hcx_candidate, "구조화된 HCX 후보 판정"

    row = run_comparison(sentence, "2025-11-04", judge_fn=judge).rows[0]

    assert row.hcx_status == "success"
    assert row.disagreement_class == expected


@pytest.mark.parametrize(
    "judge",
    [
        lambda _sentence: HcxDecision(
            None,
            "판별 응답 파싱 실패",
            "unknown",
            "HCX JSON 응답이 없습니다",
            [],
        ),
        lambda _sentence: None,
    ],
)
def test_full_comparison_separates_hcx_failure_from_success_buckets(judge) -> None:
    row = run_comparison(
        "물가는 지난해보다 2.4% 올랐다.",
        "2025-11-04",
        judge_fn=judge,
    ).rows[0]

    assert row.hcx_status != "success"
    assert row.llm_verifiable is None
    assert row.disagreement_class == HCX_ERROR


def test_disagreement_class_counts_cover_every_comparison_row() -> None:
    def judge(sentence: str) -> tuple[bool, str]:
        return ("오름세" in sentence), "독립 HCX 판정"

    result = run_comparison(
        "물가는 지난해보다 2.4% 올랐다. 먹거리 물가는 여전히 오름세를 보였다.",
        "2025-11-04",
        judge_fn=judge,
    )

    assert sum(result.disagreement_counts.values()) == len(result.rows)
    assert result.disagreement_counts == {"P+/H-": 1, "P-/H+": 1}

@pytest.mark.parametrize(
    "invalid_result",
    [
        (0, "정수 0은 bool이 아님"),
        (1, "정수 1은 bool이 아님"),
        ("", "빈 문자열은 bool이 아님"),
        (object(), "임의 객체는 bool이 아님"),
        HcxDecision(1, "정수 후보", "unknown", "잘못된 후보 타입", []),
    ],
)
def test_invalid_hcx_candidate_is_normalized_and_hybrid_fails_open(invalid_result) -> None:
    def judge(_sentence: str):
        return invalid_result

    result = run_comparison(
        "물가는 지난해보다 2.4% 올랐다.",
        "2025-11-04",
        judge_fn=judge,
    )
    row = result.rows[0]
    hybrid_row = result.mode_results["hybrid"].rows[0]

    assert row.hcx_status == "invalid_response"
    assert row.llm_verifiable is None
    assert row.disagreement_class == HCX_ERROR
    assert row.hybrid_candidate is True
    assert hybrid_row.hcx_status == "invalid_response"
    assert "보수적 유지" in hybrid_row.reason


def test_judge_result_contract_supports_structured_and_tuple_results() -> None:
    result_types = set(get_args(experiment_lab.JudgeResult))

    assert HcxDecision in result_types
    assert tuple[bool, str] in result_types
