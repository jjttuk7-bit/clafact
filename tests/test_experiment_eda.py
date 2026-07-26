from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from clafact.experiment_eda import analyze_rows


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
