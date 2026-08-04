"""Structured, explainable profiles for numeric claims in Shadow research."""
from __future__ import annotations

from dataclasses import dataclass
import re


_INDICATOR_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("물가", "소비자물가", ("소비자물가",)),
    ("물가", "물가", ("물가",)),
    ("고용", "고용률", ("고용률",)),
    ("고용", "실업률", ("실업률",)),
    ("고용", "취업자 수", ("취업자 수", "취업자")),
    ("인구", "출생아 수", ("출생아 수", "출생아")),
    ("인구", "사망자 수", ("사망자 수", "사망자")),
    ("인구", "혼인 건수", ("혼인 건수", "혼인")),
    ("인구", "이혼 건수", ("이혼 건수", "이혼")),
    ("인구", "주민등록인구", ("주민등록인구",)),
    ("인구", "인구", ("인구",)),
    ("무역", "수출액", ("수출액", "수출")),
    ("무역", "수입액", ("수입액", "수입")),
)
_ANAPHORIC_PATTERN = re.compile(r"이\s*같은|이같은|해당|그(?:는|이|러한|같은)")
_REGION_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("서울", ("서울특별시", "서울")), ("부산", ("부산광역시", "부산")),
    ("대구", ("대구광역시", "대구")), ("인천", ("인천광역시", "인천")),
    ("광주", ("광주광역시", "광주")), ("대전", ("대전광역시", "대전")),
    ("울산", ("울산광역시", "울산")), ("세종", ("세종특별자치시", "세종")),
    ("경기", ("경기도", "경기")), ("강원", ("강원특별자치도", "강원도", "강원")),
    ("충북", ("충청북도", "충북")), ("충남", ("충청남도", "충남")),
    ("전북", ("전북특별자치도", "전라북도", "전북")), ("전남", ("전라남도", "전남")),
    ("경북", ("경상북도", "경북")), ("경남", ("경상남도", "경남")),
    ("제주", ("제주특별자치도", "제주도", "제주")), ("전국", ("전국",)),
)
_PRICE_PRODUCT_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("배추", ("배추",)), ("무", ("무",)), ("쌀", ("쌀",)),
    ("사과", ("사과",)), ("달걀", ("달걀", "계란")), ("커피", ("커피",)),
)
_EMPLOYMENT_QUALIFIER_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("경제활동인구", ("경제활동인구",)),
    ("산업별", ("산업별", "산업")),
)


_POPULATION_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("청년층", ("청년층", "청년")), ("여성", ("여성", "여자")),
    ("남성", ("남성", "남자")), ("고령층", ("고령층", "고령자", "노인")),
    ("15~29세", ("15~29세", "15~29 세")),
)


@dataclass(frozen=True)
class ClaimProfile:
    """A reproducible interpretation of one numeric news sentence."""

    topic: str = ""
    indicator: str = ""
    period: str = ""
    comparison: str = ""
    unit: str = ""
    region: str = ""
    population: str = ""
    search_query: str = ""
    search_terms: tuple[str, ...] = ()
    qualifiers: tuple[str, ...] = ()
    context_inherited: bool = False


def _detect_topic_indicator(sentence: str) -> tuple[str, str]:
    compact = "".join(sentence.split())
    for topic, indicator, aliases in _INDICATOR_SPECS:
        if any("".join(alias.split()) in compact for alias in aliases):
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


def _detect_alias(sentence: str, aliases: tuple[tuple[str, tuple[str, ...]], ...]) -> str:
    compact = "".join(sentence.split())
    for canonical, values in aliases:
        if any("".join(value.split()) in compact for value in values):
            return canonical
    return ""


def _detect_qualifiers(sentence: str) -> tuple[str, ...]:
    """Return explicit terms that narrow a KOSIS table search without asserting truth."""
    qualifiers = []
    price_product = _detect_alias(sentence, _PRICE_PRODUCT_ALIASES)
    employment_qualifier = _detect_alias(sentence, _EMPLOYMENT_QUALIFIER_ALIASES)
    for value in (price_product, employment_qualifier):
        if value and value not in qualifiers:
            qualifiers.append(value)
    return tuple(qualifiers)


def _build_search_query(indicator: str, qualifiers: tuple[str, ...]) -> str:
    return " ".join((*qualifiers, indicator)).strip()


def build_claim_profile(sentence: str, *, previous: ClaimProfile | None = None) -> ClaimProfile:
    """Extract a supported numeric-claim profile without asserting factual truth."""
    topic, indicator = _detect_topic_indicator(sentence)
    qualifiers = _detect_qualifiers(sentence)
    is_price_product = any(product in qualifiers for product, _ in _PRICE_PRODUCT_ALIASES)
    if is_price_product and (not indicator or indicator == "물가") and ("가격" in sentence or "물가" in sentence):
        topic, indicator = "물가", "소비자물가"
    region = _detect_alias(sentence, _REGION_ALIASES)
    population = _detect_alias(sentence, _POPULATION_ALIASES)
    inherited = False
    if indicator in ("", "물가", "인구", "고용") and previous and previous.indicator and _ANAPHORIC_PATTERN.search(sentence):
        topic, indicator, inherited = previous.topic, previous.indicator, True
        region = region or previous.region
        population = population or previous.population
    return ClaimProfile(
        topic=topic,
        indicator=indicator,
        period=_detect_period(sentence),
        comparison=_detect_comparison(sentence),
        unit=_detect_unit(sentence),
        region=region,
        population=population,
        search_query=_build_search_query(indicator, qualifiers),
        search_terms=(*qualifiers, indicator) if indicator else qualifiers,
        qualifiers=qualifiers,
        context_inherited=inherited,
    )


def profile_summary(profile: ClaimProfile) -> str:
    """Render the extracted profile as a compact, reviewable Shadow caption."""
    suffix = " · 앞 문장 문맥 보완" if profile.context_inherited else ""
    return (
        f"주제: {profile.topic} · 지표: {profile.indicator} · 시간: {profile.period} "
        f"· 비교: {profile.comparison} · 단위: {profile.unit} · 지역: {profile.region} "
        f"· 모집단: {profile.population}{suffix}"
    )
