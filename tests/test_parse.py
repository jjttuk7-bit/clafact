"""규칙 기반 Claim Parser 테스트 (수치·시점·임계·추세)."""
from clafact.pipeline.parse import (
    extract_quantities, normalize_period, detect_op, detect_trend, parse_claim,
)


def test_extract_percent():
    q = extract_quantities("지난해 실업률은 7.2%로 전년보다 0.3%p 상승했다.")
    assert [(x.value, x.composed_unit) for x in q] == [(7.2, "%"), (0.3, "%p")]


def test_extract_scale_unit():
    """'23만 명' → 값 23, 단위 '만명', 절대값 230,000 (verdict 엔진 규격)"""
    q = extract_quantities("지난해 출생아 수는 23만 명으로 역대 최저를 기록했다.")
    assert len(q) == 1
    assert q[0].composed_unit == "만명" and q[0].normalized_value == 230000


def test_extract_comma_number():
    q = extract_quantities("2024년 총 과수 농가는 166,558가구로 집계됐다.")
    vals = [(x.value, x.unit) for x in q]
    assert (166558.0, "가구") in vals


def test_dates_not_quantities():
    """'2024년', '3월', '1분기'는 수치가 아니다"""
    assert extract_quantities("2024년 3월 1분기 발표였다.") == []


def test_bare_integer_skipped_but_decimal_kept():
    assert extract_quantities("위원 12이 참석했다.") == []  # 단위 없는 맨 정수
    q = extract_quantities("성장률이 3.5로 집계됐다.")       # 소수점은 지표성 높음
    assert q and q[0].value == 3.5


def test_compound_noun_guard():
    """규칙 A2-0006 (유래: 미니 파이프라인 E2E에서 '1인'을 수치로 오추출):
    '1인 가구'의 숫자는 복합명사의 일부 — 수량이 아니다."""
    q = extract_quantities("서울의 1인 가구는 150만 가구를 넘어섰다.")
    assert [(x.value, x.composed_unit) for x in q] == [(150.0, "만가구")]
    assert extract_quantities("3인 가족 기준으로 조사했다.") == []


def test_period_absolute():
    assert normalize_period("2024년 5월 기준이다.", "2025-03-14") == "2024-05"
    assert normalize_period("2024년 3분기 통계", "2025-03-14") == "2024-Q3"
    assert normalize_period("2024년 조사 결과", "2025-03-14") == "2024"


def test_period_relative():
    """규칙 A2-0005: 상대 시점은 기사 작성일 기준으로 정규화"""
    assert normalize_period("올해 과일 재배면적이 줄었다", "2025-03-14") == "2025"
    assert normalize_period("지난해 실업률은 7.2%였다", "2025-01-20") == "2024"
    assert normalize_period("작년 3분기부터 감소했다", "2025-06-02") == "2024-Q3"
    assert normalize_period("지난달 수출이 늘었다", "2025-01-20") == "2024-12"  # 연 경계
    assert normalize_period("내년 성장률 전망", "2025-06-02") == "2026"


def test_op_detection():
    """규칙 A2-0001 연동: 임계 표현 → 부등호"""
    assert detect_op("150만 가구를 넘어섰다") == "gte"
    assert detect_op("목표를 밑돌았다") == "lte"
    assert detect_op("1만 명에 불과했다") == "lte"
    assert detect_op("실업률은 7.2%였다") == "eq"


def test_trend_detection():
    assert detect_trend("재배면적이 1% 줄었다") == "down"
    assert detect_trend("0.3%p 상승했다") == "up"


def test_parse_claim_integration():
    pc = parse_claim("지난해 실업률은 7.2%로 전년보다 0.3%p 상승했다.", "2025-01-20")
    assert pc.parse_complete
    assert pc.period == "2024" and pc.trend == "up" and pc.op == "eq"
    assert pc.quantities[0].value == 7.2


def test_parse_incomplete_notes():
    pc = parse_claim("경제 상황이 크게 악화되었다.", "2025-01-20")
    assert not pc.parse_complete and len(pc.notes) == 2


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


def test_period_month_range_uses_article_year_and_last_month():
    assert normalize_period("1~8월 출생아 수는 16만8671명이다.", "2025-10-29") == "2025-08"
