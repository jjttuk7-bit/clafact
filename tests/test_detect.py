"""탐지 규칙 필터 테스트."""
from clafact.pipeline.detect import is_candidate


def test_number_with_unit():
    assert is_candidate("지난해 실업률은 7.2%로 전년보다 0.3%p 상승했다.")


def test_number_with_trend():
    assert is_candidate("농가 고령화에 올해 과일 재배면적이 1% 줄었다.")


def test_superlative_without_number():
    """규칙 A2-0003 (유래: F20260713142141-0828) — 숫자 없는 최상급 주장"""
    assert is_candidate("우리 동네 소상공인 매출이 사상 최악 수준으로 떨어졌다.")
    assert is_candidate("지난해 출생아 수는 역대 최저를 기록했다.")


def test_opinion_not_candidate():
    assert not is_candidate("경제 상황이 크게 악화되었다.")
    assert not is_candidate("국민 체감 경기는 갈수록 나빠지고 있다는 평가가 나온다.")


def test_date_noise_cut():
    assert not is_candidate("3월 10일")


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
