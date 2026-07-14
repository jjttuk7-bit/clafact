"""파이프라인 오케스트레이터(MVP E2E) 테스트 — Key·LLM 불필요."""
from pathlib import Path

from clafact.kosis import FixtureKosisClient
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.run import verify_article

ROOT = Path(__file__).resolve().parents[1]
IDX = StatIndex(ROOT / "data/samples/kosis/tables_meta.json")
CL = FixtureKosisClient(ROOT / "data/samples/kosis")


def _labels(text, date):
    return [(r.label, r.confidence) for r in verify_article(text, date, IDX, CL)
            if r.label != "not_claim"]


def test_derived_ratio_e2e():
    """규칙 A2-0007: 'NN세 이상 비율' 주장 → 연령 구간 합산÷전체 재현 → 일치"""
    out = _labels("2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.", "2025-03-14")
    assert out == [("match", "medium")]  # 파생 계산 경유 → medium (A2-0004)


def test_mismatch_e2e():
    out = _labels("올해 실업률이 10%에 달했다.", "2025-06-20")
    assert out == [("mismatch", "high")]


def test_threshold_and_conversion_e2e():
    out = _labels("서울의 1인 가구는 150만 가구를 넘어섰다. 지난해 출생아 수는 23만 명으로 역대 최저를 기록했다.", "2025-06-02")
    assert out == [("match", "low"), ("match", "medium")]


def test_forecast_unverifiable():
    out = _labels("내년 경제성장률은 3%에 이를 전망이다.", "2025-06-02")
    assert out == [("unverifiable", None)]


def test_opinion_not_claim():
    assert _labels("경제 상황이 크게 악화되었다.", "2025-06-20") in ([], [("unverifiable", None)])


def test_yoy_match():
    """규칙 A2-0009: 논벼 농가 383,534→364,578 = -4.9% — 증감률 재현 일치"""
    out = _labels("지난해 논벼 농가는 전년보다 4.9% 감소했다.", "2025-04-10")
    assert out == [("match", "medium")]


def test_yoy_magnitude_mismatch():
    """실제 -4.9%인데 10% 감소 주장 → 불일치"""
    out = _labels("지난해 논벼 농가는 10% 감소했다.", "2025-04-10")
    assert out and out[0][0] == "mismatch"


def test_yoy_direction_mismatch():
    """과수 농가는 실제 +0.3% 증가 — '감소' 주장은 방향 불일치"""
    rs = [r for r in verify_article("지난해 과수 농가는 2% 감소했다.", "2025-04-10", IDX, CL)
          if r.label != "not_claim"]
    assert rs[0].label == "mismatch" and "방향 불일치" in rs[0].reason


def test_yoy_metric_guard():
    """지표 가드: 농가수 통계로 '재배면적' 주장을 판정하지 않는다 (억지 판정 금지)"""
    out = _labels("지난해 과일 재배면적이 1% 줄었다.", "2025-04-10")
    assert out and out[0][0] == "unverifiable"


def test_no_table_unverifiable():
    """대응 통계 없는 주장 → 억지 매핑 없이 판단불가"""
    out = _labels("비트코인 가격이 1억 원을 넘어섰다.", "2025-06-20")
    assert out and out[0][0] == "unverifiable"


if __name__ == "__main__":
    import sys, traceback
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
    sys.exit(1 if failed else 0)
