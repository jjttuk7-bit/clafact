"""규칙 A2-0012 — 잠정치 회피 테스트.

핵심 명제: **같은 주장이라도 기사 날짜가 통계 최종수정일보다 앞서면 판단불가.**
KOSIS 는 과거 공표값(vintage)을 안 주므로, 당시 잠정치를 우리는 알 수 없다 (문서 19 §7.1).
실 API 로 LST_CHN_DE 가 행 단위로 오는 것을 확인함 (2024 데이터 = 2025-04-09).
"""
from pathlib import Path

from clafact.pipeline.run import verify_sentence, _provisional_stale
from clafact.pipeline.retrieve import StatIndex
from clafact.kosis import FixtureKosisClient
from clafact.schemas import Evidence

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다."


def _engine():
    return (StatIndex(ROOT / "data/samples/kosis/tables_meta.json"),
            FixtureKosisClient(ROOT / "data/samples/kosis"))


# ── 순수 가드 로직 ──────────────────────────────────────────
def test_stale_when_data_newer_than_article():
    evs = [Evidence(last_change_date="2025-04-09")]
    assert _provisional_stale(evs, "2025-03-14") == "2025-04-09"


def test_not_stale_when_data_older_than_article():
    evs = [Evidence(last_change_date="2025-04-09")]
    assert _provisional_stale(evs, "2025-05-14") is None


def test_not_stale_when_field_missing():
    """LST_CHN_DE 없으면 적용 안 함 — 없는 근거로 회피 남발 금지."""
    evs = [Evidence(last_change_date="")]
    assert _provisional_stale(evs, "2025-03-14") is None


def test_uses_latest_among_rows():
    """여러 행 중 가장 나중 수정일 기준 (보수적)."""
    evs = [Evidence(last_change_date="2025-01-01"),
           Evidence(last_change_date="2025-06-30")]
    assert _provisional_stale(evs, "2025-03-14") == "2025-06-30"


def test_same_day_is_not_stale():
    """최종수정일 == 기사일 이면 회피하지 않는다 (당일 값은 봤을 수 있음)."""
    evs = [Evidence(last_change_date="2025-03-14")]
    assert _provisional_stale(evs, "2025-03-14") is None


# ── E2E: 같은 주장, 날짜만 다름 ──────────────────────────────
def test_same_claim_march_is_unverifiable():
    """3월 기사 → 당시 잠정치를 모름 → 판단불가 (시연 3막)."""
    idx, client = _engine()
    r = verify_sentence(CLAIM, "2025-03-14", idx, client)
    assert r.label == "unverifiable", f"기대 판단불가, 실제 {r.label}"
    assert "A2-0012" in r.audit.get("rules", []), r.audit.get("rules")
    assert "최종수정일" in r.explanation


def test_same_claim_may_is_verifiable():
    """5월 기사 → 데이터가 이미 확정됨(4월) → 정상 판정 (시연 1막)."""
    idx, client = _engine()
    r = verify_sentence(CLAIM, "2025-05-14", idx, client)
    assert r.label == "match", f"기대 일치, 실제 {r.label}"
    assert "A2-0012" not in r.audit.get("rules", [])
    assert "64.2" in r.calculation or "64.1" in r.calculation


def test_march_vs_may_differ_only_by_date():
    """같은 문장, 날짜만 다른데 판정이 갈린다 — 규칙의 존재 이유."""
    idx, client = _engine()
    march = verify_sentence(CLAIM, "2025-03-14", idx, client)
    may = verify_sentence(CLAIM, "2025-05-14", idx, client)
    assert march.label != may.label == "match"


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
