from __future__ import annotations

from dataclasses import fields

from clafact.experiment_eda import analyze_rows
from clafact.experiment_eda_view import (
    BODY_BIN_LIMIT,
    PROBLEM_ROW_LIMIT,
    build_eda_view,
    filter_articles,
    selected_article_rows,
    _histogram,
)


def _report():
    return analyze_rows(
        [
            {
                "title": "정상",
                "date": "2025-11-04",
                "body": "물가는 2.4% 올랐다. 내년에는 더 오를 전망이다.",
            },
            {
                "title": "",
                "date": "bad",
                "body": "고용은 10만 명 늘었다. 식별번호 123은 참고값이다.",
            },
            {
                "title": "긴 기사",
                "date": "2025-11-04",
                "body": ("설명 문장입니다. " * 20) + "매출은 3억원 증가했다.",
            },
            {"title": "제외", "date": "2025-11-04", "body": ""},
        ]
    )


def test_builds_independent_kpis_and_zero_filled_known_categories():
    report = _report()
    view = build_eda_view(report)

    assert [card.key for card in view.claim_kpis] == [
        "total_sentences",
        "numeric_sentences",
        "python_candidates",
        "numeric_candidates",
        "nonnumeric_rule_candidates",
        "kosis_routed_python_candidates",
    ]
    assert [card.value for card in view.claim_kpis] == [
        report.total_sentence_count,
        report.numeric_sentence_count,
        report.python_candidate_count,
        report.numeric_candidate_count,
        report.non_numeric_candidate_count,
        report.kosis_routing_count,
    ]
    assert all("독립" in card.note or "겹칠" in card.note for card in view.claim_kpis)
    assert {row.key for row in view.quantity_rows} == {
        "percentage",
        "money",
        "people_household",
        "count_rank",
        "other",
    }
    assert {row.key for row in view.period_rows} == {
        "past",
        "current",
        "forecast",
        "unknown",
    }
    assert any(row.value == 0 for row in view.quantity_rows)
    assert any(row.value == 0 for row in view.route_rows)


def test_issue_rows_are_deterministic_private_and_bounded():
    rows = [
        {"title": f"문제 {index}", "date": "bad", "body": f"본문 {index}"}
        for index in range(PROBLEM_ROW_LIMIT + 5)
    ]
    view = build_eda_view(analyze_rows(rows))

    assert [(row.key, row.value) for row in view.issue_reason_rows] == [
        ("invalid_date", PROBLEM_ROW_LIMIT + 5)
    ]
    assert len(view.problem_rows.rows) == PROBLEM_ROW_LIMIT
    assert view.problem_rows.total == PROBLEM_ROW_LIMIT + 5
    assert view.problem_rows.truncated is True
    assert [row.row_number for row in view.problem_rows.rows] == list(
        range(1, PROBLEM_ROW_LIMIT + 1)
    )
    assert {field.name for field in fields(view.problem_rows.rows[0])} == {
        "row_number",
        "title",
        "issue",
    }


def test_single_or_empty_report_has_no_distribution_bins():
    single = build_eda_view(
        analyze_rows([{"title": "한 건", "date": "2025-11-04", "body": "물가 2% 상승"}])
    )
    empty = build_eda_view(analyze_rows([]))

    assert single.structure_chart_mode == "single"
    assert single.body_length_bins == ()
    assert single.sentence_count_bins == ()
    assert empty.structure_chart_mode == "empty"
    assert empty.body_length_bins == ()
    assert empty.sentence_count_bins == ()


def test_distribution_bins_are_aggregate_and_bounded():
    report = analyze_rows(
        [
            {
                "title": f"기사 {index}",
                "date": "2025-11-04",
                "body": ("문장입니다. " * (index + 1)),
            }
            for index in range(25)
        ]
    )
    view = build_eda_view(report)

    assert view.structure_chart_mode == "distribution"
    assert 1 <= len(view.body_length_bins) <= BODY_BIN_LIMIT
    assert 1 <= len(view.sentence_count_bins) <= BODY_BIN_LIMIT
    assert sum(row.value for row in view.body_length_bins) == 25
    assert sum(row.value for row in view.sentence_count_bins) == 25


def test_histogram_never_emits_reversed_integer_ranges_for_narrow_domain():
    rows = _histogram([1, 2] * 12 + [1])

    assert sum(row.value for row in rows) == 25
    for row in rows:
        lower, upper = (int(part) for part in row.key.split("-"))
        assert lower <= upper
    identical = _histogram([1, 1, 1])
    assert len(identical) == 1
    assert identical[0].value == 3


def test_warning_kpi_counts_only_valid_articles_but_keeps_excluded_issues():
    report = analyze_rows([{"title": "제외", "date": "bad", "body": ""}])
    view = build_eda_view(report)

    assert report.valid_article_count == 0
    assert report.warning_article_count == 0
    assert next(card for card in view.quality_kpis if card.key == "warning_articles").value == 0
    assert ("invalid_date", 1) in [
        (row.key, row.value) for row in view.issue_reason_rows
    ]
    assert view.problem_rows.total == 1

def test_filters_articles_in_source_order():
    report = _report()

    warnings = filter_articles(report, quality="warnings")
    long_rows = filter_articles(report, body_band="long")
    candidates = filter_articles(report, min_candidates=1)

    assert [article.row_number for article in warnings] == [2]
    assert [article.row_number for article in long_rows] == sorted(
        article.row_number for article in long_rows
    )
    assert all(
        sum(sentence.python_candidate for sentence in article.sentences) >= 1
        for article in candidates
    )


def test_filters_exact_zero_and_bounded_candidate_ranges():
    report = analyze_rows([
        {"title": "후보 없음", "date": "2025-11-04", "body": "설명 문장입니다."},
        {"title": "후보 있음", "date": "2025-11-04", "body": "물가는 2% 상승했다."},
    ])
    zero = filter_articles(report, min_candidates=0, max_candidates=0)
    one_or_more = filter_articles(report, min_candidates=1)

    assert zero
    assert all(
        sum(sentence.python_candidate for sentence in article.sentences) == 0
        for article in zero
    )
    assert all(
        sum(sentence.python_candidate for sentence in article.sentences) >= 1
        for article in one_or_more
    )


def test_filters_reject_unknown_modes_and_invalid_candidate_ranges():
    report = _report()

    for kwargs in (
        {"quality": "unknown"},
        {"body_band": "unknown"},
        {"min_candidates": -1},
        {"min_candidates": 2, "max_candidates": 1},
    ):
        try:
            filter_articles(report, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"ValueError expected for {kwargs}")
def test_selected_rows_are_exact_stored_sentences_and_never_expose_body():
    article = _report().articles[0]
    rows = selected_article_rows(article)

    assert [row.sentence for row in rows] == [
        sentence.text for sentence in article.sentences
    ]
    assert {field.name for field in fields(rows[0])} == {
        "sentence",
        "quantities",
        "numeric",
        "period",
        "period_class",
        "claim_type",
        "source_type",
        "route",
        "python_candidate",
        "python_rule",
        "python_reason",
    }
    assert all(not hasattr(row, "cleaned_body") for row in rows)


def test_empty_view_has_zero_kpis_and_known_zero_categories():
    view = build_eda_view(analyze_rows([]))

    assert all(card.value == 0 for card in view.quality_kpis)
    assert all(card.value == 0 for card in view.claim_kpis)
    assert all(row.value == 0 for row in view.claim_type_rows)
    assert view.problem_rows.total == 0
    assert filter_articles(analyze_rows([])) == ()
