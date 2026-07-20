"""규칙 A2-0015 — 시점 입도 불일치 회피 테스트.

유래: 첫 실 판정에서 월 단위 주장을 연 단위 통계와 대조해 오'불일치' 3건 발생.
기사는 정확했고 우리가 틀렸다 — 사실검증에서 최악의 오류 유형.
"""
from __future__ import annotations

from clafact.pipeline.retrieve import Evidence
from clafact.pipeline.run import _granularity_mismatch


def _ev(period: str) -> Evidence:
    return Evidence(tbl_id="T", org_id="101", tbl_name="소비자물가 등락률",
                    query_params={}, value=2.3, unit="%", period=period)


def test_monthly_claim_annual_evidence_is_mismatch():
    """월 주장 + 연 근거 → 회피 사유 반환."""
    s = "통계청은 지난달 소비자물가가 작년 같은 달보다 2.2% 올랐다고 밝혔다."
    assert _granularity_mismatch(s, [_ev("2024")]) is not None


def test_monthly_claim_monthly_evidence_ok():
    """월 주장 + 월 근거(YYYYMM) → 대조 가능, 회피 안 함."""
    s = "지난달 소비자물가가 전년 동월 대비 2.2% 올랐다."
    assert _granularity_mismatch(s, [_ev("202501")]) is None


def test_annual_claim_annual_evidence_ok():
    """연 주장 + 연 근거 → 애초에 대상 아님."""
    s = "지난해 연간 소비자물가 상승률은 2.3%였다."
    assert _granularity_mismatch(s, [_ev("2024")]) is None


def test_month_number_marker_detected():
    """'1월', '8월' 같은 숫자 월 표기도 월 주장으로 본다."""
    s = "소비자물가 상승률이 2%대로 올라선 것은 작년 8월 이후 5개월 만이다."
    assert _granularity_mismatch(s, [_ev("2024")]) is not None


def test_mixed_evidence_prefers_monthly():
    """근거에 월 단위가 하나라도 있으면 대조 가능으로 본다."""
    s = "지난달 소비자물가가 2.2% 올랐다."
    assert _granularity_mismatch(s, [_ev("2024"), _ev("202501")]) is None
