"""검증 실험실 CSV의 품질을 Python 규칙만으로 분석한다."""
from __future__ import annotations

import hashlib
import math
import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Iterable, Literal, Mapping

from clafact.experiment_input import clean_uploaded_article_body
from clafact.pipeline import detect, source_classify
from clafact.pipeline.ingest import FIELD_ALIASES, split_sentences
from clafact.pipeline.parse import (
    Quantity,
    extract_quantities,
    has_extractable_unit_quantity,
    has_numeric_expression,
    normalize_period,
)


IssueSeverity = Literal["warning", "excluded"]

_DATE_PREFIX = re.compile(r"^\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
_SPACES = re.compile(r"\s+")

_MESSAGES = {
    "missing_title": "제목이 없습니다.",
    "missing_date": "기사 발행일이 없습니다.",
    "invalid_date": "기사 발행일 형식을 확인할 수 없습니다.",
    "missing_body": "본문이 없습니다.",
    "empty_after_cleaning": "기사 경계 정제 후 남은 본문이 없습니다.",
    "duplicate": "앞선 행과 중복된 기사입니다.",
    "row_error": "행 값을 읽는 중 오류가 발생했습니다.",
}


@dataclass(frozen=True)
class EdaSentence:
    """업로드 본문의 정확한 문장과 Python 규칙 분석 결과."""

    text: str
    quantities: tuple[str, ...]
    numeric: bool
    period: str
    period_class: Literal["past", "current", "forecast", "unknown"]
    claim_type: str
    source_type: str
    route: str
    python_candidate: bool
    python_rule: str
    python_reason: str


@dataclass(frozen=True)
class StructureStats:
    minimum: int
    maximum: int
    mean: float
    median: float
    q1: float
    q3: float
    outlier_row_numbers: tuple[int, ...]


@dataclass(frozen=True)
class EdaIssue:
    row_number: int
    severity: IssueSeverity
    code: str
    message: str
    title: str = ""
    codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EdaArticle:
    row_number: int
    title: str
    article_date: str
    url: str
    raw_length: int
    clean_length: int
    removed_length: int
    cleaned_body: str
    warnings: tuple[str, ...]
    sentences: tuple[EdaSentence, ...] = ()


@dataclass(frozen=True)
class EdaReport:
    source_row_count: int
    articles: tuple[EdaArticle, ...]
    issues: tuple[EdaIssue, ...]
    excluded_counts: Mapping[str, int]
    warning_counts: Mapping[str, int]
    total_sentence_count: int
    numeric_sentence_count: int
    python_candidate_count: int
    numeric_candidate_count: int
    non_numeric_candidate_count: int
    kosis_routing_count: int
    quantity_type_counts: Mapping[str, int]
    period_class_counts: Mapping[str, int]
    claim_type_counts: Mapping[str, int]
    route_counts: Mapping[str, int]
    body_length_stats: StructureStats
    sentence_count_stats: StructureStats

    @property
    def valid_article_count(self) -> int:
        return len(self.articles)

    @property
    def excluded_article_count(self) -> int:
        return sum(self.excluded_counts.values())

    @property
    def warning_article_count(self) -> int:
        return sum(bool(article.warnings) for article in self.articles)


def _pick(row: Mapping[str, object], key: str, *, strip: bool = True) -> str:
    for alias in FIELD_ALIASES[key]:
        if alias in row and row[alias] is not None:
            value = str(row[alias])
            return value.strip() if strip else value
    return ""


def _date_is_valid(value: str) -> bool:
    match = _DATE_PREFIX.match(value)
    if not match:
        return False
    try:
        date(*(int(part) for part in match.groups()))
    except ValueError:
        return False
    return True


def _fingerprint(title: str, cleaned_body: str) -> str:
    # NFKC로 호환 문자와 NFC/NFD 차이만 중복 비교에서 흡수한다.
    # 표시되는 제목과 정제 본문 자체는 변경하지 않는다.
    normalized_title = _SPACES.sub(
        " ", unicodedata.normalize("NFKC", title)
    ).strip().casefold()
    normalized_body = _SPACES.sub(
        " ", unicodedata.normalize("NFKC", cleaned_body)
    ).strip()
    material = f"{normalized_title}\0{normalized_body}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _has_warning(codes: tuple[str, ...]) -> bool:
    return any(code in {"missing_title", "missing_date", "invalid_date"} for code in codes)


def _issue(
    row_number: int,
    title: str,
    exclusion: str | None,
    warnings: tuple[str, ...],
) -> EdaIssue | None:
    codes = ((exclusion,) if exclusion else ()) + warnings
    if not codes:
        return None
    severity: IssueSeverity = "excluded" if exclusion else "warning"
    message = " ".join(_MESSAGES[code] for code in codes)
    return EdaIssue(
        row_number=row_number,
        severity=severity,
        code=codes[0],
        message=message,
        title=title,
        codes=codes,
    )


def _immutable_counts(counter: Counter[str]) -> Mapping[str, int]:
    return MappingProxyType(dict(counter))


def _quantity_type(quantity: Quantity) -> str:
    if quantity.unit in {"%", "%p", "퍼센트", "포인트"}:
        return "percentage"
    if quantity.unit == "원":
        return "money"
    if quantity.unit in {"명", "인", "가구", "세대"}:
        return "people_household"
    if quantity.unit in {"건", "개", "배", "위", "호"}:
        return "count_rank"
    return "other"


def _python_evidence(
    sentence: str,
    candidate: bool,
    numeric: bool,
) -> tuple[str, str]:
    """detect.is_candidate의 실제 우선순위와 같은 규칙 이름·사유를 반환한다."""

    if not candidate:
        if detect.RE_NOISE_ONLY.match(sentence.strip()):
            return "EXCLUDED_DATE_ONLY", "날짜만 있는 식별 표현은 후보에서 제외합니다."
        if reason := detect.exclusion_reason(sentence):
            return "EXCLUDED_SITE_CHROME", reason
        if detect.RE_NUM.search(sentence) and not numeric:
            return (
                "CONTEXTUAL_NUMBER_ONLY",
                "날짜·시간 또는 복합명사 식별 숫자만 있어 수치 주장으로 보지 않습니다.",
            )
        if numeric:
            return (
                "NUMERIC_NO_CLAIM",
                "수치 표현은 있으나 단위 또는 변화·비교 조건을 충족하지 않습니다.",
            )
        return "NO_MATCH", "Python 후보 규칙에 맞는 수치·비교 표현이 없습니다."
    if has_extractable_unit_quantity(sentence):
        return "NUMERIC_UNIT", "수치+단위 표현을 탐지했습니다."
    if has_numeric_expression(sentence) and detect.RE_TREND.search(sentence):
        return "NUMERIC_TREND", "수치와 변화·비교 표현을 함께 탐지했습니다."
    if detect.RE_SUPERLATIVE.search(sentence):
        return "SUPERLATIVE", "수치 없는 사상·역대 최상급 표현을 탐지했습니다."
    rule_id = detect.which_rule(sentence)
    if rule_id:
        return rule_id, f"규칙 카드 {rule_id} 패턴을 탐지했습니다."
    return "CANDIDATE", "Python 후보 규칙을 통과했습니다."


def _period_key(period: str) -> tuple[int, int] | None:
    if match := re.fullmatch(r"(\d{4})-(\d{2})", period):
        month = int(match.group(2))
        return (int(match.group(1)), month) if 1 <= month <= 12 else None
    if match := re.fullmatch(r"(\d{4})-Q([1-4])", period):
        return int(match.group(1)), int(match.group(2)) * 3
    if match := re.fullmatch(r"(\d{4})", period):
        return int(match.group(1)), 0
    return None


def _period_class(
    period: str,
    claim_type: str,
    article_date: date | None,
) -> Literal["past", "current", "forecast", "unknown"]:
    if claim_type == "전망형":
        return "forecast"
    if not period or article_date is None:
        return "unknown"
    key = _period_key(period)
    if key is None:
        return "unknown"
    year, marker = key
    if year < article_date.year:
        return "past"
    if year > article_date.year:
        return "forecast"
    if marker == 0:
        return "current"
    if marker < article_date.month:
        return "past"
    if marker == article_date.month or (
        "-Q" in period and ((article_date.month - 1) // 3 + 1) == marker // 3
    ):
        return "current"
    return "forecast"


def _profile_sentences(cleaned_body: str, article_date: str) -> tuple[EdaSentence, ...]:
    valid_date: date | None = None
    if match := _DATE_PREFIX.match(article_date):
        try:
            valid_date = date(*(int(part) for part in match.groups()))
        except ValueError:
            pass

    rows: list[EdaSentence] = []
    for sentence in split_sentences(cleaned_body):
        quantities = extract_quantities(sentence)
        candidate = detect.is_candidate(sentence)
        numeric = (
            has_numeric_expression(sentence)
            and not detect.RE_NOISE_ONLY.match(sentence.strip())
            and not detect.exclusion_reason(sentence)
        )
        python_rule, python_reason = _python_evidence(sentence, candidate, numeric)
        source = source_classify.classify(sentence)
        period = normalize_period(sentence, valid_date) if valid_date is not None else ""
        rows.append(
            EdaSentence(
                text=sentence,
                quantities=tuple(quantity.raw for quantity in quantities),
                numeric=numeric,
                period=period,
                period_class=_period_class(period, source.claim_type, valid_date),
                claim_type=source.claim_type,
                source_type=source.source_type,
                route=source.route,
                python_candidate=candidate,
                python_rule=python_rule,
                python_reason=python_reason,
            )
        )
    return tuple(rows)


def _nearest_rank(values: list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(percentile * len(ordered)) - 1)])


def _structure_stats(values: list[int], row_numbers: list[int]) -> StructureStats:
    if not values:
        return StructureStats(0, 0, 0.0, 0.0, 0.0, 0.0, ())
    q1 = _nearest_rank(values, 0.25)
    q3 = _nearest_rank(values, 0.75)
    outliers: tuple[int, ...] = ()
    if len(values) >= 4:
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = tuple(
            row_number
            for value, row_number in zip(values, row_numbers)
            if value < low or value > high
        )
    return StructureStats(
        minimum=min(values),
        maximum=max(values),
        mean=statistics.fmean(values),
        median=float(statistics.median(values)),
        q1=q1,
        q3=q3,
        outlier_row_numbers=outliers,
    )

def analyze_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    row_number_start: int = 1,
) -> EdaReport:
    """행별 오류를 격리해 CSV 품질과 정제된 유효 기사만 반환한다."""

    articles: list[EdaArticle] = []
    issues: list[EdaIssue] = []
    excluded_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    seen_keys: set[tuple[str, str]] = set()
    source_row_count = 0

    for row_number, row in enumerate(rows, start=row_number_start):
        source_row_count += 1
        try:
            title = _pick(row, "title")
            article_date = _pick(row, "date")
            url = _pick(row, "url")
            raw_body = _pick(row, "body", strip=False)

            warnings: list[str] = []
            if not title:
                warnings.append("missing_title")
            if not article_date:
                warnings.append("missing_date")
            elif not _date_is_valid(article_date):
                warnings.append("invalid_date")
            warning_tuple = tuple(warnings)
            warning_counts.update(warning_tuple)

            exclusion: str | None = None
            cleaned_body = ""
            if not raw_body.strip():
                exclusion = "missing_body"
            else:
                cleaned_body = clean_uploaded_article_body(raw_body)
                if not cleaned_body:
                    exclusion = "empty_after_cleaning"
                else:
                    key = (
                        ("url", url)
                        if url
                        else ("fingerprint", _fingerprint(title, cleaned_body))
                    )
                    if key in seen_keys:
                        exclusion = "duplicate"
                    else:
                        seen_keys.add(key)

            if exclusion:
                excluded_counts[exclusion] += 1
            else:
                articles.append(
                    EdaArticle(
                        row_number=row_number,
                        title=title,
                        article_date=article_date,
                        url=url,
                        raw_length=len(raw_body),
                        clean_length=len(cleaned_body),
                        removed_length=max(0, len(raw_body) - len(cleaned_body)),
                        cleaned_body=cleaned_body,
                        warnings=warning_tuple,
                        sentences=_profile_sentences(cleaned_body, article_date),
                    )
                )

            issue = _issue(row_number, title, exclusion, warning_tuple)
            if issue:
                issues.append(issue)
        except Exception:
            excluded_counts["row_error"] += 1
            issues.append(
                EdaIssue(
                    row_number=row_number,
                    severity="excluded",
                    code="row_error",
                    message=_MESSAGES["row_error"],
                    codes=("row_error",),
                )
            )

    sentence_rows = tuple(
        sentence for article in articles for sentence in article.sentences
    )
    quantity_type_counts: Counter[str] = Counter()
    period_class_counts: Counter[str] = Counter()
    claim_type_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    for article in articles:
        for sentence in article.sentences:
            extracted = extract_quantities(sentence.text)
            quantity_type_counts.update(_quantity_type(quantity) for quantity in extracted)
            if sentence.python_candidate:
                period_class_counts[sentence.period_class] += 1
                claim_type_counts[sentence.claim_type] += 1
                route_counts[sentence.route] += 1

    row_numbers = [article.row_number for article in articles]
    body_lengths = [article.clean_length for article in articles]
    sentence_counts = [len(article.sentences) for article in articles]
    return EdaReport(
        source_row_count=source_row_count,
        articles=tuple(articles),
        issues=tuple(issues),
        excluded_counts=_immutable_counts(excluded_counts),
        warning_counts=_immutable_counts(warning_counts),
        total_sentence_count=len(sentence_rows),
        numeric_sentence_count=sum(sentence.numeric for sentence in sentence_rows),
        python_candidate_count=sum(sentence.python_candidate for sentence in sentence_rows),
        numeric_candidate_count=sum(
            sentence.python_candidate and sentence.numeric for sentence in sentence_rows
        ),
        non_numeric_candidate_count=sum(
            sentence.python_candidate and not sentence.numeric for sentence in sentence_rows
        ),
        kosis_routing_count=sum(
            sentence.python_candidate and sentence.route == "KOSIS_RETRIEVAL"
            for sentence in sentence_rows
        ),
        quantity_type_counts=_immutable_counts(quantity_type_counts),
        period_class_counts=_immutable_counts(period_class_counts),
        claim_type_counts=_immutable_counts(claim_type_counts),
        route_counts=_immutable_counts(route_counts),
        body_length_stats=_structure_stats(body_lengths, row_numbers),
        sentence_count_stats=_structure_stats(sentence_counts, row_numbers),
    )
