"""LLM 2차 판별 테스트 — MockLLMClient로 오프라인 검증.

실 HCX 응답 구조는 test_hcx_contract.py(record-replay)가 별도로 지킨다.
여기서는 판별 로직·파싱·정밀화 배선을 Mock으로 고정한다.
"""
from __future__ import annotations

from clafact.llm import MockLLMClient
from clafact.pipeline import detect_llm


def _mock_verifiable(user: str) -> str:
    """휴리스틱 목: 연도/순번/나이/시세는 검증 불가, 나머지는 가능."""
    kill = ["2024년", "2025년", "1위", "2위", "세 ", "살", "코스피", "주가", "환율"]
    verifiable = not any(k in user for k in kill)
    return f'{{"verifiable": {str(verifiable).lower()}, "reason": "mock"}}'


def _client():
    m = MockLLMClient()
    m.on("검증 가능한 수치 주장", _mock_verifiable)
    return m


def test_judge_passes_real_claim():
    ok, _ = detect_llm.judge("지난해 실업률은 7.2%로 상승했다.", _client())
    assert ok is True


def test_judge_rejects_year_number():
    ok, reason = detect_llm.judge("이 사건은 2024년에 일어났다.", _client())
    assert ok is False


def test_judge_rejects_market_price():
    ok, _ = detect_llm.judge("코스피가 3000선을 넘었다.", _client())
    assert ok is False


def test_refine_filters_false_positives():
    """규칙 필터가 관대하게 잡은 후보에서 검증 불가 문장이 걸러진다."""
    candidates = [
        (0, "지난해 출생아 수는 23만 명이었다."),   # 통과
        (1, "그는 올해 65살이 되었다."),            # 나이 → 컷
        (2, "물가가 3.1% 올랐다."),                # 통과
        (3, "코스피가 3000을 넘었다."),            # 시세 → 컷
    ]
    kept = detect_llm.refine(candidates, _client())
    kept_idx = [i for i, _ in kept]
    assert kept_idx == [0, 2]


def test_parse_malformed_is_conservative():
    """판별 응답이 깨지면 보수적으로 통과 (재현율 보호 — 놓치는 것보다 낫다)."""
    m = MockLLMClient(default="이건 JSON이 아님")
    ok, reason = detect_llm.judge("실업률 7.2%", m)
    assert ok is True and "파싱" in reason


def test_parse_extracts_from_noisy_json():
    """설명이 섞인 응답에서도 JSON 블록을 뽑아낸다."""
    m = MockLLMClient(default='분석 결과: {"verifiable": false, "reason": "연도"} 입니다')
    ok, _ = detect_llm.judge("2024년 사건", m)
    assert ok is False
