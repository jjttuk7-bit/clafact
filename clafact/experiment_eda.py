"""검증 실험실 CSV의 품질을 Python 규칙만으로 분석한다."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Iterable, Literal, Mapping

from clafact.experiment_input import clean_uploaded_article_body
from clafact.pipeline.ingest import FIELD_ALIASES


IssueSeverity = Literal["warning", "excluded"]

_DATE_PREFIX = re.compile(r"^\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})")
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
    """후속 문장 분석이 채울 자리. Task 1에서는 문장을 생성하지 않는다."""

    text: str


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

    @property
    def valid_article_count(self) -> int:
        return len(self.articles)

    @property
    def excluded_article_count(self) -> int:
        return sum(self.excluded_counts.values())

    @property
    def warning_article_count(self) -> int:
        return sum(1 for issue in self.issues if issue.codes and _has_warning(issue.codes))


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
    normalized_title = _SPACES.sub(" ", title).strip().casefold()
    normalized_body = _SPACES.sub(" ", cleaned_body).strip()
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


def analyze_rows(rows: Iterable[Mapping[str, object]]) -> EdaReport:
    """행별 오류를 격리해 CSV 품질과 정제된 유효 기사만 반환한다."""

    articles: list[EdaArticle] = []
    issues: list[EdaIssue] = []
    excluded_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    seen_keys: set[tuple[str, str]] = set()
    source_row_count = 0

    for row_number, row in enumerate(rows, start=1):
        source_row_count = row_number
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

    return EdaReport(
        source_row_count=source_row_count,
        articles=tuple(articles),
        issues=tuple(issues),
        excluded_counts=_immutable_counts(excluded_counts),
        warning_counts=_immutable_counts(warning_counts),
    )
