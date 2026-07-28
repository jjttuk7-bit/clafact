"""Structured, explainable profiles for numeric claims in Shadow research."""
from __future__ import annotations

from dataclasses import dataclass
import re


_TOPIC_INDICATORS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("물가", ("소비자물가", "물가")),
    ("고용", ("고용률", "실업률", "취업자 수", "취업자")),
    ("인구", ("출생아 수", "출생아", "주민등록인구", "인구")),
)
_ANAPHORIC_PATTERN = re.compile(r"이\s*같은|이같은|해당|그(?:는|이|러한|같은)")


@dataclass(frozen=True)
class ClaimProfile:
    """A reproducible interpretation of one numeric news sentence."""

    topic: str = ""
    indicator: str = ""
    period: str = ""
    comparison: str = ""
    unit: str = ""
    search_query: str = ""
    context_inherited: bool = False


def _detect_topic_indicator(sentence: str) -> tuple[str, str]:
    compact = "".join(sentence.split())
    for topic, indicators in _TOPIC_INDICATORS:
        for indicator in indicators:
            if "".join(indicator.split()) in compact:
                return topic, indicator
    return "", ""


def _detect_period(sentence: str) -> str:
    if re.search(r"\d{1,2}월|지난달|이번달|전년동월", sentence):
        return "월"
    if "분기" in sentence:
        return "분기"
    if any(token in sentence for token in ("지난해", "올해", "전년", "연간")):
        return "연"
    return ""


def _detect_comparison(sentence: str) -> str:
    if any(token in sentence for token in ("전년동월", "지난해 같은 달", "지난해같은달")):
        return "전년동월비"
    if "전월" in sentence:
        return "전월비"
    if any(token in sentence for token in ("전년보다", "전년 대비", "지난해보다")):
        return "전년 대비"
    return ""


def _detect_unit(sentence: str) -> str:
    if "%p" in sentence or "퍼센트포인트" in sentence:
        return "%p"
    if "%" in sentence or "퍼센트" in sentence:
        return "%"
    if "명" in sentence:
        return "명"
    if "건" in sentence:
        return "건"
    return ""


def build_claim_profile(sentence: str, *, previous: ClaimProfile | None = None) -> ClaimProfile:
    """Extract a supported numeric-claim profile without asserting factual truth."""
    topic, indicator = _detect_topic_indicator(sentence)
    inherited = False
    if indicator in ("", "물가", "인구", "고용") and previous and previous.indicator and _ANAPHORIC_PATTERN.search(sentence):
        topic, indicator, inherited = previous.topic, previous.indicator, True
    return ClaimProfile(
        topic=topic,
        indicator=indicator,
        period=_detect_period(sentence),
        comparison=_detect_comparison(sentence),
        unit=_detect_unit(sentence),
        search_query=indicator,
        context_inherited=inherited,
    )
