"""LLM 2차 판별 (FR-02 정밀도 보강) — 규칙 필터 뒤에 붙는다.

설계(문서 03 §2.2): 규칙 필터(detect.py)는 재현율을 책임지고 관대하게 잡는다.
이 모듈은 그 후보 중 '검증 불가능한 수치'(연도·순번·나이·시세추정·의견)를 걸러
정밀도를 올린다. 판정이 아니라 **탐지 정밀화**임에 주의 — LLM은 여기까지만.

키 없으면 MockLLMClient로 동작(전량 통과, 개발용). 키 있으면 HCX.
실 응답은 record-replay 카세트로 회귀 검증(tests/test_hcx_contract.py).
"""
from __future__ import annotations

import json
import re

from clafact.llm import LLMClient, get_client

# 판별 프롬프트 — record_hcx.py 의 CASES 및 계약 테스트와 동일 계열(system 문구 일치).
SYSTEM = (
    "당신은 뉴스 문장이 '공식 통계로 검증 가능한 수치 주장'인지 판별하는 분류기다. "
    "다음은 검증 대상이 아니다: 연도·날짜·순번·나이·전화번호 같은 식별용 숫자, "
    "주가·환율 등 실시간 시세, 개인 발언 속 추정, 순수 의견·전망. "
    '반드시 JSON으로만 답하라: {"verifiable": true|false, "reason": "짧은 근거"}'
)

_JSON = re.compile(r"\{.*\}", re.S)


def _parse(resp: str) -> tuple[bool, str]:
    """LLM 응답에서 verifiable 추출 — 파싱 실패 시 보수적으로 통과(재현율 보호)."""
    m = _JSON.search(resp or "")
    if not m:
        return True, "판별 응답 파싱 실패 → 보수적 통과"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return True, "판별 JSON 파싱 실패 → 보수적 통과"
    return bool(obj.get("verifiable", True)), str(obj.get("reason", ""))


def judge(sentence: str, client: LLMClient | None = None) -> tuple[bool, str]:
    """단일 문장의 검증 가능성 2차 판별. (통과여부, 근거)."""
    client = client or get_client()
    resp = client.complete(SYSTEM, f"다음 문장을 판별하라: {sentence}")
    return _parse(resp)


def refine(candidates: list[tuple[int, str]],
           client: LLMClient | None = None) -> list[tuple[int, str]]:
    """규칙 필터 후보 리스트를 2차 판별로 정밀화.

    입력: detect.filter_sentences() 결과 [(idx, sentence), ...]
    출력: verifiable=True 로 남은 것만. 판별 근거는 호출측이 필요하면 judge()로.
    """
    client = client or get_client()
    kept = []
    for idx, s in candidates:
        ok, _reason = judge(s, client)
        if ok:
            kept.append((idx, s))
    return kept
