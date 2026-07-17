"""규칙 A2-0013 — 지수 기준연도 회피 테스트 (문서 19 §7.3).

핵심: 지수는 기준연도에 따라 값이 달라진다(2015=100 vs 2020=100). 기사는 기준연도를
명시하지 않으므로, **지수 '수준' 주장은 판단불가**로 회피한다. 단 **상승률·증감률은
기준연도 불변**이므로 회피하지 않는다 — 이 구분이 규칙의 핵심.
"""
from pathlib import Path

from clafact.pipeline.run import verify_sentence, _index_base_year, _is_index_level_claim
from clafact.pipeline.parse import Quantity
from clafact.pipeline.retrieve import StatIndex
from clafact.kosis import FixtureKosisClient

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data/samples/kosis_baseyear"


def _engine():
    return (StatIndex(FIX / "tables_meta.json"), FixtureKosisClient(FIX))


# ── 기준연도 추출 ──────────────────────────────────────────
def test_extract_base_year():
    assert _index_base_year("소비자물가지수(2020=100)") == "2020"
    assert _index_base_year("품목별 소비자물가지수(품목성질별: 2015=100)") == "2015"


def test_non_index_returns_none():
    assert _index_base_year("경영주 연령별 농가") is None       # 지수 아님
    assert _index_base_year("과수 재배면적(ha)") is None


# ── 수준 vs 율 구분 ────────────────────────────────────────
def test_index_level_is_flagged():
    q = Quantity(value=114.2, unit="", raw="114.2")
    assert _is_index_level_claim("소비자물가지수가 114.2를 기록했다.", q) is True


def test_rate_is_not_flagged():
    """상승률(%+추세)은 기준연도 불변 → 회피 안 함."""
    q = Quantity(value=3.6, unit="%", raw="3.6%")
    assert _is_index_level_claim("소비자물가지수가 3.6% 상승했다.", q) is False


def test_non_index_sentence_not_flagged():
    q = Quantity(value=114.2, unit="", raw="114.2")
    assert _is_index_level_claim("과수 농가가 114.2만 가구다.", q) is False  # '지수' 없음


# ── E2E ────────────────────────────────────────────────────
def test_index_level_claim_unverifiable():
    """지수 수준 주장 → A2-0013 → 판단불가."""
    idx, client = _engine()
    r = verify_sentence("지난해 소비자물가지수는 114.2를 기록했다.", "2025-06-01", idx, client)
    assert r.label == "unverifiable", f"기대 판단불가, 실제 {r.label}"
    assert "A2-0013" in r.audit.get("rules", []), r.audit.get("rules")
    assert "기준연도" in r.explanation and "2020" in r.explanation


def test_rate_claim_not_blocked_by_baseyear():
    """상승률 주장은 A2-0013 에 걸리지 않는다 (기준연도 불변)."""
    idx, client = _engine()
    r = verify_sentence("지난해 소비자물가지수가 3.6% 상승했다.", "2025-06-01", idx, client)
    assert "A2-0013" not in (r.audit.get("rules", []) if r.audit else [])


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
