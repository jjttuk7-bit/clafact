"""HCX 계약 테스트 — record-replay 기반 (@contract) + 실호출 스모크 (@live).

계약: 우리 파이프라인이 HCX에 기대하는 것 —
  ① complete()가 비어있지 않은 문자열을 준다
  ② 판별 프롬프트의 응답이 JSON으로 파싱되고 'verifiable' 키를 가진다
카세트(tests/cassettes/hcx/smoke.json)가 있어야 실행. 없으면 skip(녹화 필요).
카세트는 scripts/record_hcx.py 로 R2가 키 있는 환경에서 녹화한다.
"""
from __future__ import annotations

import json
import os

import pytest


@pytest.mark.contract
def test_replay_returns_nonempty(hcx_cassette):
    """녹화된 요청은 비어있지 않은 응답을 재생한다."""
    calls = hcx_cassette.cassette.entries
    assert calls, "카세트가 비어 있음 — 재녹화 필요"
    for sig, e in calls.items():
        assert e["response"], f"빈 응답 (sig={sig})"


@pytest.mark.contract
def test_replay_no_key_in_cassette(hcx_cassette):
    """카세트에 API 키/시크릿이 새지 않는다 (공개 커밋 안전)."""
    blob = json.dumps(hcx_cassette.cassette.entries, ensure_ascii=False)
    assert "Bearer " not in blob
    assert "HCX_API_KEY" not in blob
    # 실제 키 값이 환경에 있으면 그 문자열이 카세트에 없는지 확인
    key = os.environ.get("HCX_API_KEY")
    if key:
        assert key not in blob


@pytest.mark.contract
def test_verifiable_prompt_contract(hcx_cassette):
    """판별 프롬프트 계열 응답은 JSON이고 'verifiable' 불리언을 가진다.

    (판별 프롬프트에 한함 — system에 '검증 가능한 수치 주장인지 판별' 포함)
    """
    checked = 0
    for e in hcx_cassette.cassette.entries.values():
        if "판별하는 분류기" not in e["system"]:
            continue
        try:
            obj = json.loads(e["response"])
        except json.JSONDecodeError:
            pytest.fail(f"판별 응답이 JSON 아님: {e['response'][:80]!r}")
        assert "verifiable" in obj and isinstance(obj["verifiable"], bool)
        checked += 1
    if checked == 0:
        pytest.skip("판별 프롬프트 케이스가 카세트에 없음")


@pytest.mark.live
def test_hcx_live_smoke():
    """실 HCX 1회 호출 — 키 유효성·엔드포인트 검증. `-m live` 로만 실행."""
    if not os.environ.get("HCX_API_KEY"):
        pytest.skip("HCX_API_KEY 없음 — live 스모크 불가")
    from clafact.llm import HcxClient
    resp = HcxClient().complete(
        "예/아니오로만 답하라.",
        "다음 문장에 수치가 있는가: 실업률은 7.2%였다.",
    )
    assert isinstance(resp, str) and resp.strip(), "빈 응답 — 엔드포인트/모델/쿼터 확인"
