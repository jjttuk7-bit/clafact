from clafact.claim_profile import build_claim_profile, profile_summary


def test_extracts_population_profile_from_numeric_claim():
    profile = build_claim_profile("지난해 출생아 수는 23만 명으로 전년보다 감소했다.")

    assert profile.topic == "인구"
    assert profile.indicator == "출생아 수"
    assert profile.period == "연"
    assert profile.comparison == "전년 대비"
    assert profile.unit == "명"
    assert profile.search_query == "출생아 수"


def test_extracts_employment_profile_from_numeric_claim():
    profile = build_claim_profile("지난해 고용률은 62.7%로 전년보다 0.3%p 상승했다.")

    assert profile.topic == "고용"
    assert profile.indicator == "고용률"
    assert profile.comparison == "전년 대비"
    assert profile.unit == "%p"
    assert profile.search_query == "고용률"


def test_detects_export_value_as_trade_indicator():
    profile = build_claim_profile("7월 수출은 13% 증가했다.")

    assert profile.topic == "무역"
    assert profile.indicator == "수출액"
    assert profile.period == "월"
    assert profile.unit == "%"
    assert profile.search_query == "수출액"


def test_distinguishes_employment_rate_from_employed_people():
    rate = build_claim_profile("고용률은 62.7%다.")
    people = build_claim_profile("취업자는 2800만명이다.")

    assert rate.indicator == "고용률"
    assert people.indicator == "취업자 수"

def test_extracts_region_and_population_as_independent_claim_axes():
    profile = build_claim_profile("2025년 3월 서울 청년층 실업률은 7.5%였다.")

    assert profile.region == "서울"
    assert profile.population == "청년층"
    assert "지역: 서울" in profile_summary(profile)
    assert "모집단: 청년층" in profile_summary(profile)


def test_inherits_indicator_for_anaphoric_followup_sentence():
    previous = build_claim_profile("10월 소비자물가가 2.4% 상승했다.")
    profile = build_claim_profile("이같은 물가 상승률은 15개월 만에 가장 높다.", previous=previous)

    assert profile.topic == "물가"
    assert profile.indicator == "소비자물가"
    assert profile.context_inherited is True
    assert profile.search_query == "소비자물가"


def test_formats_profile_summary_with_context_provenance():
    previous = build_claim_profile("10월 소비자물가가 2.4% 상승했다.")
    profile = build_claim_profile("이같은 물가 상승률은 15개월 만에 가장 높다.", previous=previous)

    assert profile_summary(profile) == (
        "주제: 물가 · 지표: 소비자물가 · 시간:  · 비교:  · 단위:  · 지역:  · 모집단:  · 앞 문장 문맥 보완"
    )

def test_preserves_cabbage_as_a_price_claim_qualifier_for_kosis_search():
    profile = build_claim_profile("10월 배추 가격은 전년동월 대비 34.5% 하락했다.")

    assert profile.topic == "물가"
    assert profile.indicator == "소비자물가"
    assert profile.qualifiers == ("배추",)
    assert profile.search_query == "배추 소비자물가"


def test_detects_death_count_as_a_supported_population_indicator():
    profile = build_claim_profile("지난해 사망자 수는 전년보다 증가했다.")

    assert profile.topic == "인구"
    assert profile.indicator == "사망자 수"
    assert profile.search_query == "사망자 수"


def test_preserves_economically_active_population_as_an_employment_qualifier():
    profile = build_claim_profile("경제활동인구 가운데 취업자는 전년보다 늘었다.")

    assert profile.topic == "고용"
    assert profile.indicator == "취업자 수"
    assert profile.qualifiers == ("경제활동인구",)
    assert profile.search_query == "경제활동인구 취업자 수"


def test_product_price_sentence_normalizes_generic_price_word_to_consumer_price():
    profile = build_claim_profile("배추(-34.5%), 무(-40.5%) 등은 물가 상승률을 보였다.")

    assert profile.indicator == "소비자물가"
    assert profile.search_query == "배추 소비자물가"
