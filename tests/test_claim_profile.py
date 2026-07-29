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
        "주제: 물가 · 지표: 소비자물가 · 시간:  · 비교:  · 단위:  · 앞 문장 문맥 보완"
    )