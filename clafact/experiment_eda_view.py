"""검증 실험실 EDA를 렌더러와 분리한 불변 뷰 모델."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from clafact.experiment_eda import EdaArticle, EdaReport, StructureStats


BODY_BIN_LIMIT = 10
PROBLEM_ROW_LIMIT = 100

_ISSUE_ORDER = (
    "missing_body",
    "empty_after_cleaning",
    "duplicate",
    "row_error",
    "missing_title",
    "missing_date",
    "invalid_date",
)
_QUANTITY_CATEGORIES = (
    ("percentage", "비율·퍼센트"),
    ("money", "금액"),
    ("people_household", "인원·가구"),
    ("count_rank", "건수·배수·순위"),
    ("other", "기타 단위"),
)
_PERIOD_CATEGORIES = (
    ("past", "과거"),
    ("current", "현재"),
    ("forecast", "전망"),
    ("unknown", "시점 불명"),
)
_CLAIM_CATEGORIES = tuple(
    (key, key) for key in ("규모형", "증감형", "파생계산형", "전망형", "임계형", "순위형")
)
_ROUTE_CATEGORIES = (
    ("KOSIS_RETRIEVAL", "KOSIS 조회"),
    ("NON_KOSIS_QUEUE", "비KOSIS 검토"),
    ("OUT_OF_SCOPE", "범위 밖"),
    ("HUMAN_REVIEW", "사람 검토"),
)


@dataclass(frozen=True)
class KpiCard:
    key: str
    label: str
    value: int
    note: str


@dataclass(frozen=True)
class CountRow:
    key: str
    label: str
    value: int


@dataclass(frozen=True)
class ProblemRow:
    row_number: int
    title: str
    issue: str


@dataclass(frozen=True)
class ProblemRows:
    rows: tuple[ProblemRow, ...]
    total: int
    limit: int
    truncated: bool


@dataclass(frozen=True)
class StructureSummary:
    body_length: StructureStats
    sentence_count: StructureStats


@dataclass(frozen=True)
class SelectedSentenceRow:
    sentence: str
    quantities: tuple[str, ...]
    numeric: bool
    period: str
    period_class: str
    claim_type: str
    source_type: str
    route: str
    python_candidate: bool
    python_rule: str
    python_reason: str


@dataclass(frozen=True)
class EdaView:
    quality_kpis: tuple[KpiCard, ...]
    claim_kpis: tuple[KpiCard, ...]
    issue_reason_rows: tuple[CountRow, ...]
    problem_rows: ProblemRows
    structure_chart_mode: Literal["empty", "single", "distribution"]
    structure_stats: StructureSummary
    body_length_bins: tuple[CountRow, ...]
    sentence_count_bins: tuple[CountRow, ...]
    quantity_rows: tuple[CountRow, ...]
    period_rows: tuple[CountRow, ...]
    claim_type_rows: tuple[CountRow, ...]
    route_rows: tuple[CountRow, ...]


_INDEPENDENT_NOTE = "서로 겹칠 수 있는 독립 집계이며 단계별 퍼널이 아닙니다."


def _kpi(key: str, label: str, value: int, note: str) -> KpiCard:
    return KpiCard(key=key, label=label, value=int(value), note=note)


def _category_rows(counts: object, categories: tuple[tuple[str, str], ...]) -> tuple[CountRow, ...]:
    getter = getattr(counts, "get")
    return tuple(
        CountRow(key=key, label=label, value=int(getter(key, 0)))
        for key, label in categories
    )


def _histogram(values: list[int]) -> tuple[CountRow, ...]:
    if not values:
        return ()
    low, high = min(values), max(values)
    if low == high:
        return (CountRow(str(low), f"{low:,}", len(values)),)
    bin_count = min(
        BODY_BIN_LIMIT,
        high - low + 1,
        max(1, math.ceil(math.sqrt(len(values)))),
    )
    width = max(1, math.ceil((high - low + 1) / bin_count))
    bin_count = math.ceil((high - low + 1) / width)
    buckets = [0] * bin_count
    for value in values:
        index = min((value - low) // width, bin_count - 1)
        buckets[index] += 1
    return tuple(
        CountRow(
            key=f"{low + index * width}-{min(high, low + (index + 1) * width - 1)}",
            label=f"{low + index * width:,}–{min(high, low + (index + 1) * width - 1):,}",
            value=count,
        )
        for index, count in enumerate(buckets)
    )


def _issue_rows(report: EdaReport) -> tuple[CountRow, ...]:
    combined = {
        key: int(report.excluded_counts.get(key, 0))
        + int(report.warning_counts.get(key, 0))
        for key in set(report.excluded_counts) | set(report.warning_counts)
    }
    ordered = [key for key in _ISSUE_ORDER if combined.get(key)]
    ordered.extend(sorted(key for key, value in combined.items() if value and key not in _ISSUE_ORDER))
    return tuple(CountRow(key=key, label=key, value=combined[key]) for key in ordered)


def _problem_rows(report: EdaReport) -> ProblemRows:
    ordered = sorted(report.issues, key=lambda issue: (issue.row_number, issue.code))
    rows = tuple(
        ProblemRow(issue.row_number, issue.title, issue.message)
        for issue in ordered[:PROBLEM_ROW_LIMIT]
    )
    return ProblemRows(
        rows=rows,
        total=len(ordered),
        limit=PROBLEM_ROW_LIMIT,
        truncated=len(ordered) > PROBLEM_ROW_LIMIT,
    )


def build_eda_view(report: EdaReport) -> EdaView:
    """EDA 보고서를 크기가 제한된 렌더링 중립 뷰 모델로 변환한다."""

    article_count = report.valid_article_count
    mode: Literal["empty", "single", "distribution"] = (
        "empty" if article_count == 0 else "single" if article_count == 1 else "distribution"
    )
    body_values = [article.clean_length for article in report.articles]
    sentence_values = [len(article.sentences) for article in report.articles]
    distributions = mode == "distribution"
    return EdaView(
        quality_kpis=(
            _kpi("source_rows", "원본 행", report.source_row_count, "업로드 CSV에서 읽은 전체 행입니다."),
            _kpi("valid_articles", "유효 기사", article_count, "본문 정제를 통과한 기사입니다."),
            _kpi("excluded_articles", "제외 기사", report.excluded_article_count, "분석에서 제외된 기사입니다."),
            _kpi("warning_articles", "품질 경고 기사", report.warning_article_count, "유효 기사 중 분석에는 포함되지만 확인이 필요한 기사입니다."),
        ),
        claim_kpis=(
            _kpi("total_sentences", "전체 문장", report.total_sentence_count, _INDEPENDENT_NOTE),
            _kpi("numeric_sentences", "수치 포함 문장", report.numeric_sentence_count, _INDEPENDENT_NOTE),
            _kpi("python_candidates", "Python 후보", report.python_candidate_count, _INDEPENDENT_NOTE),
            _kpi("numeric_candidates", "수치형 Python 후보", report.numeric_candidate_count, _INDEPENDENT_NOTE),
            _kpi("nonnumeric_rule_candidates", "비수치 규칙 후보", report.non_numeric_candidate_count, _INDEPENDENT_NOTE),
            _kpi(
                "kosis_routed_python_candidates",
                "KOSIS 라우팅 Python 후보",
                report.kosis_routing_count,
                _INDEPENDENT_NOTE,
            ),
        ),
        issue_reason_rows=_issue_rows(report),
        problem_rows=_problem_rows(report),
        structure_chart_mode=mode,
        structure_stats=StructureSummary(
            body_length=report.body_length_stats,
            sentence_count=report.sentence_count_stats,
        ),
        body_length_bins=_histogram(body_values) if distributions else (),
        sentence_count_bins=_histogram(sentence_values) if distributions else (),
        quantity_rows=_category_rows(report.quantity_type_counts, _QUANTITY_CATEGORIES),
        period_rows=_category_rows(report.period_class_counts, _PERIOD_CATEGORIES),
        claim_type_rows=_category_rows(report.claim_type_counts, _CLAIM_CATEGORIES),
        route_rows=_category_rows(report.route_counts, _ROUTE_CATEGORIES),
    )


def filter_articles(
    report: EdaReport,
    *,
    quality: Literal["all", "warnings", "outliers", "clean"] = "all",
    body_band: Literal["all", "short", "typical", "long"] = "all",
    min_candidates: int = 0,
    max_candidates: int | None = None,
) -> tuple[EdaArticle, ...]:
    """품질·본문 길이·후보 수로 기사 목록을 원본 행 순서대로 제한한다."""

    if quality not in {"all", "warnings", "outliers", "clean"}:
        raise ValueError(f"unknown quality filter: {quality}")
    if body_band not in {"all", "short", "typical", "long"}:
        raise ValueError(f"unknown body band: {body_band}")
    if min_candidates < 0:
        raise ValueError("min_candidates must be non-negative")
    if max_candidates is not None and max_candidates < min_candidates:
        raise ValueError("max_candidates must be greater than or equal to min_candidates")

    outliers = set(report.body_length_stats.outlier_row_numbers) | set(
        report.sentence_count_stats.outlier_row_numbers
    )
    q1, q3 = report.body_length_stats.q1, report.body_length_stats.q3
    selected: list[EdaArticle] = []
    for article in sorted(report.articles, key=lambda item: item.row_number):
        if quality == "warnings" and not article.warnings:
            continue
        if quality == "outliers" and article.row_number not in outliers:
            continue
        if quality == "clean" and (article.warnings or article.row_number in outliers):
            continue
        if body_band == "short" and article.clean_length > q1:
            continue
        if body_band == "typical" and not (q1 < article.clean_length <= q3):
            continue
        if body_band == "long" and article.clean_length <= q3:
            continue
        candidate_count = sum(sentence.python_candidate for sentence in article.sentences)
        if candidate_count < min_candidates:
            continue
        if max_candidates is not None and candidate_count > max_candidates:
            continue
        selected.append(article)
    return tuple(selected)

def selected_article_rows(article: EdaArticle) -> tuple[SelectedSentenceRow, ...]:
    """저장된 문장과 그 근거만 노출한다. 기사 본문은 뷰 모델에 복사하지 않는다."""

    return tuple(
        SelectedSentenceRow(
            sentence=sentence.text,
            quantities=sentence.quantities,
            numeric=sentence.numeric,
            period=sentence.period,
            period_class=sentence.period_class,
            claim_type=sentence.claim_type,
            source_type=sentence.source_type,
            route=sentence.route,
            python_candidate=sentence.python_candidate,
            python_rule=sentence.python_rule,
            python_reason=sentence.python_reason,
        )
        for sentence in article.sentences
    )
