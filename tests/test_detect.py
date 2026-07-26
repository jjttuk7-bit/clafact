"""탐지 규칙 필터 테스트."""
from clafact.pipeline import detect
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


def test_date_number_with_trend_is_not_a_candidate_but_mixed_value_is():
    assert not is_candidate("2025년 생산은 증가했다.")
    assert not is_candidate("3월 생산은 증가했다.")
    assert not is_candidate("1분기 생산은 증가했다.")
    assert is_candidate("2025년 생산량은 500 증가했다.")


def test_compound_number_does_not_mask_the_actual_candidate_branch():
    assert not is_candidate("3인 가구는 증가했다.")
    assert is_candidate("3인 가구는 20% 증가했다.")
    assert is_candidate("3인 가구는 생산량 500 증가했다.")


def test_rejects_live_news_chrome_before_claim_detection() -> None:
    sentence = "실시간 뉴스 10분 전 [사이언스샷] 인간은 또 다른 원숭이"

    assert detect.exclusion_reason(sentence) == "실시간 뉴스·사이트 크롬"
    assert detect.is_candidate(sentence) is False

def test_piece_count_is_a_numeric_unit_candidate():
    sentence = "판매량은 3개였다."

    assert detect.has_extractable_unit_quantity(sentence)
    assert is_candidate(sentence)


def test_month_duration_is_not_a_piece_count_candidate():
    assert not is_candidate("조사는 3개월간 진행됐다.")
    assert is_candidate("판매량은 3개였다.")