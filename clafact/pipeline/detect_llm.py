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
from dataclasses import dataclass, replace

from clafact.llm import LLMClient, get_client

_JSON = re.compile(r"\{.*\}", re.S)

# HCX는 후보 탐지와 근거 충분성을 분리한다. 후보가 된다고 해서 기사 안에
# 공식 통계표가 이미 있다는 뜻은 아니며, needs_retrieval은 정상적인 후보 상태다.
SYSTEM = (
    "당신은 뉴스 문장의 검증 가능한 수치 주장 후보 탐지와 기사 내부 근거 충분성을 분리하는 분류기다. "
    "먼저 수치·비교·증감·최고/최저·시점이 있어 후속 검증 대상이 될 수 있으면 candidate=true로 판정하라. "
    "연도·날짜·순번·나이·전화번호 같은 식별용 숫자, 실시간 시세, 순수 의견·전망만 candidate=false다. "
    "candidate=true인 문장이 기사 안에 공식 통계표·기관 직접 인용을 충분히 담지 않아도 false로 바꾸지 말고 "
    "evidence_status=needs_retrieval로 표시하라. "
    "원문에 실제로 있는 짧은 구간만 quoted_spans에 넣어라. "
    '반드시 JSON으로만 답하라: {"candidate": true|false, "candidate_reason": "짧은 근거", '
    '"evidence_status": "sufficient|needs_retrieval|not_applicable|unknown", '
    '"evidence_reason": "짧은 근거", "quoted_spans": ["원문 구간"]}'
)


@dataclass(frozen=True)
class HcxDecision:
    candidate: bool | None
    candidate_reason: str
    evidence_status: str
    evidence_reason: str
    quoted_spans: list[str]

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


def _parse_decision(resp: str) -> HcxDecision:
    """HCX 구조화 응답을 파싱하며, 실패를 거짓 미탐지로 바꾸지 않는다."""
    m = _JSON.search(resp or "")
    if not m:
        return HcxDecision(None, "판별 응답 파싱 실패", "unknown", "HCX JSON 응답이 없습니다", [])
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return HcxDecision(None, "판별 JSON 파싱 실패", "unknown", "HCX JSON이 깨졌습니다", [])

    if "candidate" not in obj:
        # 이전 카세트와 기존 응답은 호환을 유지한다.
        candidate = bool(obj.get("verifiable", True))
        reason = str(obj.get("reason", "기존 HCX 응답"))
        return HcxDecision(candidate, reason, "unknown", "기존 응답에는 근거 상태가 없습니다", [])

    candidate = obj.get("candidate")
    if not isinstance(candidate, bool):
        return HcxDecision(None, "candidate 값이 불완전함", "unknown", "HCX 응답 형식 오류", [])
    status = str(obj.get("evidence_status", "unknown"))
    if status not in {"sufficient", "needs_retrieval", "not_applicable", "unknown"}:
        status = "unknown"
    spans = obj.get("quoted_spans", [])
    if not isinstance(spans, list):
        spans = []
    return HcxDecision(
        candidate,
        str(obj.get("candidate_reason", "HCX 후보 판정 사유 없음")),
        status,
        str(obj.get("evidence_reason", "HCX 근거 상태 사유 없음")),
        [str(span) for span in spans],
    )


def judge_decision(sentence: str, client: LLMClient | None = None) -> HcxDecision:
    """단일 문장의 HCX 후보 판정과 기사 내부 근거 상태를 반환한다."""
    client = client or get_client()
    decision = _parse_decision(client.complete(SYSTEM, f"다음 문장을 판별하라: {sentence}"))
    # 모델의 인용은 입력 문장에 실제 존재하는 경우에만 노출한다.
    quoted_spans = [span for span in decision.quoted_spans if span and span in sentence]
    return replace(decision, quoted_spans=quoted_spans)


def judge(sentence: str, client: LLMClient | None = None) -> tuple[bool, str]:
    """기존 파이프라인 호환용 후보 판정 API."""
    decision = judge_decision(sentence, client)
    if decision.candidate is None:
        return True, f"{decision.candidate_reason} → 보수적 통과"
    return decision.candidate, decision.candidate_reason


def assist(sentence: str, client: LLMClient | None = None) -> tuple[bool, bool]:
    """규칙 후보를 보존하고 HCX의 판별 신호만 반환한다."""
    signal, _reason = judge(sentence, client)
    return True, signal


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
