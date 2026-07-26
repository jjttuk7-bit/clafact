from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from clafact.experiment_eda import analyze_rows
from clafact.pipeline.ingest import split_sentences


def test_analyze_rows_records_missing_invalid_and_duplicate_rows():
    rows = [
        {
            "title": "정상",
            "date": "2025-11-04",
            "url": "https://n/1",
            "body": "입력 2025.11.04. 09:00 소비자물가는 2.4% 올랐다.",
        },
        {"title": "", "date": "not-a-date", "url": "https://n/2", "body": "본문"},
        {"title": "본문 없음", "date": "2025-11-04", "url": "https://n/3", "body": ""},
        {
            "title": "중복",
            "date": "2025-11-04",
            "url": "https://n/1",
            "body": "다른 본문",
        },
    ]

    report = analyze_rows(rows)

    assert report.source_row_count == 4
    assert report.valid_article_count == 2
    assert report.excluded_article_count == 2
    assert dict(report.excluded_counts) == {"missing_body": 1, "duplicate": 1}
    assert report.warning_counts["missing_title"] == 1
    assert report.warning_counts["invalid_date"] == 1
    assert [issue.row_number for issue in report.issues] == [2, 3, 4]
    assert report.issues[0].codes == ("missing_title", "invalid_date")
    assert report.issues[0].severity == "warning"
    assert report.issues[1].severity == "excluded"


def test_analyze_rows_reuses_all_supported_field_aliases():
    report = analyze_rows(
        [
            {
                "기사 제목": "별칭 제목",
                "게시일": "2025/11/04 오전 9시",
                "링크": "https://n/alias",
                "기사 본문 전체": "별칭 본문입니다.",
            }
        ]
    )

    article = report.articles[0]
    assert article.title == "별칭 제목"
    assert article.article_date == "2025/11/04 오전 9시"
    assert article.url == "https://n/alias"
    assert article.cleaned_body == "별칭 본문입니다."


def test_url_is_the_duplicate_key_when_it_exists():
    report = analyze_rows(
        [
            {"title": "첫 기사", "date": "2025-01-01", "url": "u1", "body": "본문 A"},
            {"title": "다른 기사", "date": "2025-01-02", "url": "u1", "body": "본문 B"},
            {"title": "첫 기사", "date": "2025-01-03", "url": "u2", "body": "본문 A"},
        ]
    )

    assert [article.row_number for article in report.articles] == [1, 3]
    assert dict(report.excluded_counts) == {"duplicate": 1}


def test_missing_url_uses_normalized_title_and_cleaned_body_fingerprint():
    report = analyze_rows(
        [
            {"title": "  같은   제목 ", "date": "2025-01-01", "body": "같은   본문"},
            {"title": "같은 제목", "date": "2025-01-02", "body": "같은 본문"},
        ]
    )

    assert report.valid_article_count == 1
    assert report.excluded_counts["duplicate"] == 1
    assert report.issues[0].row_number == 2


def test_boundary_cleaned_empty_body_is_distinct_from_missing_body():
    report = analyze_rows(
        [
            {
                "title": "경계만 존재",
                "date": "",
                "body": "관련 기사 뒤에 있는 텍스트는 기사 본문이 아닙니다.",
            }
        ]
    )

    assert report.valid_article_count == 0
    assert dict(report.excluded_counts) == {"empty_after_cleaning": 1}
    assert dict(report.warning_counts) == {"missing_date": 1}
    assert report.issues[0].codes == ("empty_after_cleaning", "missing_date")
    assert report.issues[0].severity == "excluded"


def test_raw_clean_and_removed_lengths_measure_the_uploaded_value():
    raw = "메뉴 입력 2025.11.04. 09:00  소비자물가는  2.4% 올랐다. 관련 기사 부속"
    report = analyze_rows(
        [{"title": "길이", "date": "2025.11.04", "url": "u", "body": raw}]
    )

    article = report.articles[0]
    assert article.raw_length == len(raw)
    assert article.cleaned_body == "소비자물가는 2.4% 올랐다."
    assert article.clean_length == len(article.cleaned_body)
    assert article.removed_length == len(raw) - len(article.cleaned_body)


@pytest.mark.parametrize(
    "article_date",
    [
        "2025-11-04",
        "2025/11/04 09:30",
        "2025.11.04. 오전 9시",
    ],
)
def test_common_date_prefixes_are_valid(article_date):
    report = analyze_rows(
        [{"title": "날짜", "date": article_date, "body": "정상 본문입니다."}]
    )

    assert "invalid_date" not in report.warning_counts
    assert "missing_date" not in report.warning_counts


def test_invalid_calendar_date_is_a_warning_and_does_not_exclude_article():
    report = analyze_rows(
        [{"title": "날짜", "date": "2025.13.42", "body": "정상 본문입니다."}]
    )

    assert report.valid_article_count == 1
    assert dict(report.warning_counts) == {"invalid_date": 1}
    assert report.articles[0].article_date == "2025.13.42"


@pytest.mark.parametrize(
    "article_date",
    [
        "2025-11-040",
        "2025/01/01123",
        "2025.11.041",
    ],
)
def test_date_prefix_rejects_an_extra_digit_after_the_day(article_date):
    report = analyze_rows(
        [{"title": "날짜", "date": article_date, "body": "정상 본문입니다."}]
    )

    assert dict(report.warning_counts) == {"invalid_date": 1}


def test_fallback_fingerprint_normalizes_nfkc_without_mutating_articles():
    report = analyze_rows(
        [
            {
                "title": "ＡＢＣ 가격",
                "date": "2025-01-01",
                "body": "증가율은 ２．４％입니다.",
            },
            {
                "title": "ABC 가격",
                "date": "2025-01-02",
                "body": "증가율은 2.4%입니다.",
            },
        ]
    )

    assert report.valid_article_count == 1
    assert report.excluded_counts["duplicate"] == 1
    assert report.articles[0].title == "ＡＢＣ 가격"
    assert report.articles[0].cleaned_body == "증가율은 ２．４％입니다."


def test_fallback_fingerprint_treats_nfc_and_nfd_hangul_as_equal():
    import unicodedata

    nfc_title = "경제"
    nfd_title = unicodedata.normalize("NFD", nfc_title)
    report = analyze_rows(
        [
            {"title": nfc_title, "date": "2025-01-01", "body": "같은 본문"},
            {"title": nfd_title, "date": "2025-01-02", "body": "같은 본문"},
        ]
    )

    assert nfc_title != nfd_title
    assert report.valid_article_count == 1
    assert report.excluded_counts["duplicate"] == 1


def test_original_row_numbers_are_preserved_after_exclusions():
    report = analyze_rows(
        [
            {"title": "없음", "date": "2025-01-01", "body": ""},
            {"title": "유효", "date": "2025-01-01", "body": "유효 본문"},
            {"title": "유효2", "date": "2025-01-02", "body": "다른 본문"},
        ]
    )

    assert [article.row_number for article in report.articles] == [2, 3]
    assert report.issues[0].row_number == 1


def test_analyze_rows_can_preserve_source_labels_for_a_selected_csv_range():
    report = analyze_rows(
        [
            {"title": "첫째", "date": "2025-01-01", "body": "첫 본문"},
            {"title": "둘째", "date": "2025-01-02", "body": ""},
        ],
        row_number_start=1001,
    )

    assert report.source_row_count == 2
    assert report.articles[0].row_number == 1001
    assert report.issues[0].row_number == 1002


def test_issue_records_do_not_expose_raw_or_cleaned_bodies():
    raw_secret = "외부에 노출하면 안 되는 전체 원문"
    report = analyze_rows(
        [
            {"title": "기준", "date": "2025-01-01", "url": "u", "body": "기준 본문"},
            {"title": "제외", "date": "", "url": "u", "body": raw_secret},
        ]
    )

    issue = report.issues[-1]
    assert not hasattr(issue, "raw_body")
    assert not hasattr(issue, "cleaned_body")
    assert raw_secret not in repr(issue)


def test_models_are_immutable():
    report = analyze_rows([{"title": "제목", "date": "2025-01-01", "body": "본문"}])

    with pytest.raises(FrozenInstanceError):
        report.source_row_count = 99
    with pytest.raises(FrozenInstanceError):
        report.articles[0].title = "변조"
    with pytest.raises(TypeError):
        report.warning_counts["x"] = 1


class _BrokenValue:
    def __str__(self):
        raise ValueError("broken value")


def test_one_bad_row_is_recorded_without_aborting_later_rows():
    report = analyze_rows(
        [
            {"title": "오류", "date": "2025-01-01", "body": _BrokenValue()},
            {"title": "후속", "date": "2025-01-02", "body": "후속 정상 본문"},
        ]
    )

    assert report.source_row_count == 2
    assert [article.row_number for article in report.articles] == [2]
    assert dict(report.excluded_counts) == {"row_error": 1}
    assert report.issues[0].codes == ("row_error",)

def test_sentence_and_aggregate_profiles_reuse_existing_python_rules():
    body = (
        "지난달 소비자물가는 2.4% 상승했다. "
        "회사는 매출 3억 원을 기록했다. "
        "전체 인구는 5만 명으로 집계됐다. "
        "내년 물가는 3.0% 오를 전망이다. "
        "시장은 안정적이다."
    )

    report = analyze_rows(
        [{"title": "수치 기사", "date": "2025-11-04", "body": body}]
    )

    assert report.total_sentence_count == 5
    assert report.numeric_sentence_count == 4
    assert report.python_candidate_count == 4
    assert report.kosis_routing_count >= 1
    assert dict(report.quantity_type_counts) == {
        "percentage": 2,
        "money": 1,
        "people_household": 1,
    }
    assert report.period_class_counts["past"] == 1
    assert report.period_class_counts["forecast"] == 1
    assert report.route_counts["KOSIS_RETRIEVAL"] >= 1
    assert report.claim_type_counts["전망형"] == 1

    sentences = report.articles[0].sentences
    assert tuple(item.text for item in sentences) == tuple(split_sentences(body))
    assert all(item.text in report.articles[0].cleaned_body for item in sentences)
    assert sentences[0].quantities == ("2.4%",)
    assert sentences[0].period == "2025-10"
    assert sentences[0].period_class == "past"
    assert sentences[0].source_type == "KOSIS_BUT_COMPLEX"
    assert sentences[0].route == "KOSIS_RETRIEVAL"
    assert sentences[0].python_candidate is True
    assert sentences[0].python_rule == "NUMERIC_UNIT"
    assert "수치+단위" in sentences[0].python_reason
    assert sentences[3].period_class == "forecast"
    assert sentences[4].quantities == ()
    assert sentences[4].python_candidate is False
    assert sentences[4].python_rule == "NO_MATCH"


@pytest.mark.parametrize(
    ("sentence", "expected_type"),
    [
        ("증가율은 2.4%였다.", "percentage"),
        ("증가폭은 0.3%p였다.", "percentage"),
        ("비율은 3퍼센트였다.", "percentage"),
        ("격차는 2포인트였다.", "percentage"),
        ("예산은 3억 원이었다.", "money"),
        ("인구는 5만 명이었다.", "people_household"),
        ("가구는 2천 세대였다.", "people_household"),
        ("거래는 8건이었다.", "count_rank"),
        ("순위는 2위였다.", "count_rank"),
        ("면적은 3㎢였다.", "other"),
    ],
)
def test_quantity_type_mapping_is_deterministic(sentence, expected_type):
    report = analyze_rows(
        [{"title": "단위", "date": "2025-11-04", "body": sentence}]
    )

    assert dict(report.quantity_type_counts) == {expected_type: 1}


def test_invalid_article_date_never_fabricates_a_period():
    sentence = "지난달 소비자물가는 2.4% 상승했다."
    report = analyze_rows(
        [{"title": "날짜 오류", "date": "not-a-date", "body": sentence}]
    )

    profiled = report.articles[0].sentences[0]
    assert profiled.quantities == ("2.4%",)
    assert profiled.route == "KOSIS_RETRIEVAL"
    assert profiled.period == ""
    assert profiled.period_class == "unknown"


@pytest.mark.parametrize("article_date", ["", "   ", "not-a-date", "2025.13.42"])
def test_missing_or_invalid_article_date_never_uses_the_current_date(article_date):
    report = analyze_rows(
        [
            {
                "title": "날짜 없음",
                "date": article_date,
                "body": "지난달 소비자물가는 2.4% 상승했다.",
            }
        ]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.period == ""
    assert sentence.period_class == "unknown"


def test_every_eda_sentence_is_an_exact_uploaded_cleaned_sentence():
    uploaded_body = (
        "입력 2025.11.04. 09:00 첫 문장은 물가가 2.4% 올랐다고 밝혔다. "
        "둘째 문장은 생산량이 500 증가했다고 설명했다. "
        "관련 기사 이 문장부터는 기사 본문이 아니다."
    )

    report = analyze_rows(
        [{"title": "원문 보존", "date": "2025-11-04", "body": uploaded_body}]
    )
    article = report.articles[0]
    expected = tuple(split_sentences(article.cleaned_body))

    assert tuple(sentence.text for sentence in article.sentences) == expected
    assert all(sentence.text in article.cleaned_body for sentence in article.sentences)
    assert all(sentence.text in uploaded_body for sentence in article.sentences)
    assert "기사 본문이 아니다" not in " ".join(
        sentence.text for sentence in article.sentences
    )


@pytest.mark.parametrize(
    ("article_date", "sentence", "expected_period", "expected_class"),
    [
        ("2025-11-04", "내년 인구는 3만 명이다.", "2026", "forecast"),
        ("2025-03-04", "올해 8월 인구는 3만 명이다.", "2025-08", "forecast"),
        ("2025-03-04", "2025년 4분기 인구는 3만 명이다.", "2025-Q4", "forecast"),
        ("2025-11-04", "지난달 인구는 3만 명이다.", "2025-10", "past"),
        ("2025-11-04", "올해 11월 인구는 3만 명이다.", "2025-11", "current"),
        ("invalid", "내년 인구는 3만 명이다.", "", "unknown"),
    ],
)
def test_period_class_compares_normalized_period_with_valid_article_date(
    article_date,
    sentence,
    expected_period,
    expected_class,
):
    report = analyze_rows(
        [{"title": "시점", "date": article_date, "body": sentence}]
    )

    profiled = report.articles[0].sentences[0]
    assert profiled.period == expected_period
    assert profiled.period_class == expected_class


def test_bare_integer_with_trend_is_a_numeric_python_candidate():
    report = analyze_rows(
        [{"title": "수치", "date": "2025-11-04", "body": "생산량은 500 증가했다."}]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.quantities == ()
    assert sentence.numeric is True
    assert sentence.python_candidate is True
    assert sentence.python_rule == "NUMERIC_TREND"
    assert report.numeric_sentence_count == 1


def test_contextual_date_number_with_trend_is_not_numeric_or_candidate():
    report = analyze_rows(
        [{"title": "날짜", "date": "2025-11-04", "body": "2025년 생산은 증가했다."}]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.numeric is False
    assert sentence.python_candidate is False
    assert sentence.python_rule == "CONTEXTUAL_NUMBER_ONLY"
    assert "날짜·시간" in sentence.python_reason
    assert report.numeric_sentence_count == 0
    assert report.python_candidate_count == 0


def test_mixed_date_and_bare_value_remains_numeric_and_candidate():
    report = analyze_rows(
        [
            {
                "title": "혼합",
                "date": "2025-11-04",
                "body": "2025년 생산량은 500 증가했다.",
            }
        ]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.numeric is True
    assert sentence.python_candidate is True
    assert report.numeric_sentence_count == 1
    assert report.python_candidate_count == 1


@pytest.mark.parametrize(
    ("text", "numeric", "candidate", "rule", "quantities"),
    [
        ("3인 가구는 증가했다.", False, False, "CONTEXTUAL_NUMBER_ONLY", ()),
        ("3인 가구는 20% 증가했다.", True, True, "NUMERIC_UNIT", ("20%",)),
        ("3인 가구는 생산량 500 증가했다.", True, True, "NUMERIC_TREND", ()),
    ],
)
def test_compound_guard_keeps_eda_evidence_on_the_actual_branch(
    text,
    numeric,
    candidate,
    rule,
    quantities,
):
    report = analyze_rows(
        [{"title": "복합명사", "date": "2025-11-04", "body": text}]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.numeric is numeric
    assert sentence.python_candidate is candidate
    assert sentence.python_rule == rule
    assert sentence.quantities == quantities


def test_candidate_counts_separate_numeric_and_non_numeric_rules():
    body = (
        "생산량은 500 증가했다. "
        "매출은 20% 증가했다. "
        "우리 동네 매출은 사상 최고 수준이다."
    )
    report = analyze_rows(
        [{"title": "후보 분해", "date": "2025-11-04", "body": body}]
    )

    assert report.numeric_sentence_count == 2
    assert report.python_candidate_count == 3
    assert report.numeric_candidate_count == 2
    assert report.non_numeric_candidate_count == 1
    assert (
        report.numeric_candidate_count + report.non_numeric_candidate_count
        == report.python_candidate_count
    )


@pytest.mark.parametrize(
    ("text", "expected_rule", "reason_fragment", "expected_numeric"),
    [
        ("2025년 11월 4일", "EXCLUDED_DATE_ONLY", "날짜", False),
        (
            "실시간 뉴스 2분 전 소비자물가는 2.4% 상승했다.",
            "EXCLUDED_SITE_CHROME",
            "실시간 뉴스·사이트 크롬",
            False,
        ),
        ("식별번호는 500이다.", "NUMERIC_NO_CLAIM", "수치 표현", True),
        ("시장은 안정적이다.", "NO_MATCH", "수치·비교 표현", False),
    ],
)
def test_non_candidates_report_the_actual_exclusion_path(
    text,
    expected_rule,
    reason_fragment,
    expected_numeric,
):
    report = analyze_rows(
        [{"title": "제외", "date": "2025-11-04", "body": text}]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.numeric is expected_numeric
    assert sentence.python_candidate is False
    assert sentence.python_rule == expected_rule
    assert reason_fragment in sentence.python_reason
    assert report.numeric_sentence_count == int(expected_numeric)


def test_structure_statistics_use_nearest_rank_and_iqr_original_rows():
    rows = [
        {"title": "a", "date": "2025-01-01", "body": "가."},
        {"title": "b", "date": "2025-01-01", "body": "나다."},
        {"title": "c", "date": "2025-01-01", "body": "라마바."},
        {
            "title": "d",
            "date": "2025-01-01",
            "body": (
                "아" * 100
                + "다. 둘째 문장이다. 셋째 문장이다. "
                + "넷째 문장이다. 다섯째 문장이다."
            ),
        },
    ]

    report = analyze_rows(rows)
    body_stats = report.body_length_stats
    sentence_stats = report.sentence_count_stats
    body_lengths = [article.clean_length for article in report.articles]

    assert body_stats.minimum == min(body_lengths)
    assert body_stats.maximum == max(body_lengths)
    assert body_stats.mean == pytest.approx(sum(body_lengths) / 4)
    assert body_stats.median == pytest.approx(
        (sorted(body_lengths)[1] + sorted(body_lengths)[2]) / 2
    )
    assert body_stats.q1 == sorted(body_lengths)[0]
    assert body_stats.q3 == sorted(body_lengths)[2]
    assert body_stats.outlier_row_numbers == (4,)
    assert sentence_stats.minimum == 1
    assert sentence_stats.maximum == 5
    assert sentence_stats.q1 == 1
    assert sentence_stats.q3 == 1
    assert sentence_stats.outlier_row_numbers == (4,)


def test_structure_statistics_do_not_label_outliers_below_four_articles():
    report = analyze_rows(
        [
            {"title": "a", "date": "2025-01-01", "body": "짧다."},
            {"title": "b", "date": "2025-01-01", "body": "아" * 500 + "다."},
            {"title": "c", "date": "2025-01-01", "body": "보통 길이다."},
        ]
    )

    assert report.body_length_stats.outlier_row_numbers == ()
    assert report.sentence_count_stats.outlier_row_numbers == ()


def test_piece_count_is_numeric_candidate_and_count_rank_in_eda():
    report = analyze_rows(
        [{"title": "개수", "date": "2025-11-04", "body": "판매량은 3개였다."}]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.quantities == ("3개",)
    assert sentence.numeric is True
    assert sentence.python_candidate is True
    assert sentence.python_rule == "NUMERIC_UNIT"
    assert dict(report.quantity_type_counts) == {"count_rank": 1}


def test_month_duration_is_not_numeric_or_count_rank_in_eda():
    report = analyze_rows(
        [{"title": "조사 기간", "date": "2025-11-04", "body": "조사는 3개월간 진행됐다."}]
    )

    sentence = report.articles[0].sentences[0]
    assert sentence.quantities == ()
    assert sentence.numeric is False
    assert sentence.python_candidate is False
    assert report.numeric_sentence_count == 0
    assert report.python_candidate_count == 0
    assert dict(report.quantity_type_counts) == {}