"""판정 엔진 단위 테스트 — "테스트 없는 규칙은 등록 불가" (문서 11 A2).

실행: python -m tests.test_verdict  (pytest 있으면 pytest 도 동작)
"""
from clafact.pipeline.verdict import compare, derived_ratio, normalize, rounded_match
from clafact.schemas import VerdictLabel, MismatchType


def test_derived_ratio_kosis_case():
    """클라비 제시 사례: 과수 농가 고령화 106,877/166,558 ≈ 64.2%"""
    ratio = derived_ratio([33840, 27218, 22904, 22915], 166558) * 100
    assert abs(ratio - 64.168) < 0.01
    res = compare(64.2, "%", ratio, "%")
    assert res.verdict.label == VerdictLabel.MATCH, res.verdict.reason


def test_simple_match():
    res = compare(7.2, "%", 7.2, "%")
    assert res.verdict.label == VerdictLabel.MATCH


def test_clear_mismatch():
    """노션 예시: 기사 10% vs 공식 7.2% → 불일치"""
    res = compare(10.0, "%", 7.2, "%")
    assert res.verdict.label == VerdictLabel.MISMATCH
    assert res.verdict.mismatch_type == MismatchType.VALUE


def test_percent_vs_percent_point():
    """%와 %p 혼동은 불일치로 잡는다 (함정형)"""
    res = compare(2.0, "%", 2.0, "%p")
    assert res.verdict.label == VerdictLabel.MISMATCH
    assert "%p" in res.verdict.reason


def test_threshold_gte():
    """규칙 A2-0001: '150만 가구를 넘어섰다' — 공식 151.2만이므로 임계 충족 → 일치.
    유래: 첫 하네스 실행에서 등호 비교로 오판된 실패 케이스."""
    res = compare(150, "만가구", 1512340, "가구", op="gte")
    assert res.verdict.label == VerdictLabel.MATCH, res.verdict.calculation
    # 공식 수치가 임계 미달이면 불일치
    res2 = compare(150, "만가구", 1480000, "가구", op="gte")
    assert res2.verdict.label == VerdictLabel.MISMATCH


def test_rounding_in_claimed_units():
    """규칙 A2-0002: 반올림은 기사 단위 스케일 기준.
    '23만 명' vs 공식 230,028명 → 23.0028만 → round=23 → 일치."""
    res = compare(23, "만명", 230028, "명")
    assert res.verdict.label == VerdictLabel.MATCH, res.verdict.calculation


def test_unknown_unit_family_unverifiable():
    """환산 불가 단위 계열 → 판단불가 (억지 판정 금지)"""
    res = compare(5.0, "%", 5.0, "가구")
    assert res.verdict.label == VerdictLabel.UNVERIFIABLE


def test_rounding_boundary():
    """반올림 규칙: 기사 64.2 vs 공식 64.168 일치, 64.25 이상이면 64.3 이므로 불일치"""
    assert rounded_match(64.2, 64.168)
    assert not rounded_match(64.2, 64.26)


def test_area_conversion():
    """1㎢ = 100ha"""
    v, fam = normalize(3.5, "㎢")
    assert v == 350.0 and fam == "area_ha"


def test_relative_tolerance():
    """반올림으로는 안 맞아도 상대 오차 0.5% 이내면 일치"""
    res = compare(1000.0, "명", 1004.0, "명")  # 오차 0.4%
    assert res.verdict.label == VerdictLabel.MATCH
    res2 = compare(1000.0, "명", 1020.0, "명")  # 오차 2%
    assert res2.verdict.label == VerdictLabel.MISMATCH


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
