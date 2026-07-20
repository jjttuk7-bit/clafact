"""규칙 A2-0016 — 비교 기준(항목) 정합 테스트.

유래: 시점·표를 모두 맞췄는데도 전월비(0.7%)를 집어 '전년 동월 대비 2.2%' 주장을
오'불일치' 판정. 같은 표·같은 시점이라도 항목이 다르면 다른 수치다.
"""
from __future__ import annotations

from clafact.pipeline.retrieve import Evidence
from clafact.pipeline.run import _claim_basis, _pick_basis, _prefer_total_index


def _ev(itm: str, value: float, c1: str = "총지수") -> Evidence:
    return Evidence(tbl_id="T", org_id="101", tbl_name="월별 소비자물가 등락률",
                    query_params={"itm": itm, "c1": c1}, value=value,
                    unit="%", period="202501")


ROWS = [_ev("전월비", 0.7), _ev("전년동월비(%)", 2.2), _ev("전년누계비(%)", 2.2)]


def test_basis_detection():
    assert _claim_basis("지난달 소비자물가가 전년 동월 대비 2.2% 올랐다.") == "전년동월"
    assert _claim_basis("지난달 소비자물가가 작년 같은 달보다 2.2% 올랐다.") == "전년동월"
    assert _claim_basis("소비자물가가 전월 대비 0.7% 올랐다.") == "전월"
    assert _claim_basis("소비자물가가 올랐다.") == ""


def test_picks_yoy_not_mom():
    """'전년 동월 대비' 주장 → 전년동월비 행만 남는다 (전월비 0.7% 배제)."""
    sel = _pick_basis(ROWS, "전년동월")
    assert len(sel) == 1 and sel[0].value == 2.2


def test_picks_mom_when_claimed():
    sel = _pick_basis(ROWS, "전월")
    assert len(sel) == 1 and sel[0].value == 0.7


def test_missing_basis_returns_empty():
    """기준 항목이 없으면 빈 리스트 → 상위에서 판단불가로 흐른다."""
    assert _pick_basis([_ev("전월비", 0.7)], "전년동월") == []


def test_no_basis_keeps_all():
    """주장이 기준을 안 밝히면 거르지 않는다."""
    assert _pick_basis(ROWS, "") == ROWS


def test_prefers_total_index():
    """지수종류 미지정 주장 → 총지수."""
    evs = [_ev("전년동월비", 1.5, c1="생활물가지수"), _ev("전년동월비", 2.2, c1="총지수")]
    sel = _prefer_total_index(evs, "지난달 소비자물가가 2.2% 올랐다.")
    assert len(sel) == 1 and sel[0].value == 2.2


def test_named_index_is_respected():
    """기사가 생활물가지수를 직접 부르면 총지수로 바꾸지 않는다."""
    evs = [_ev("전년동월비", 1.5, c1="생활물가지수"), _ev("전년동월비", 2.2, c1="총지수")]
    sel = _prefer_total_index(evs, "생활물가지수가 1.5% 올랐다.")
    assert len(sel) == 2
