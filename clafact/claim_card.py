"""Reviewed, reproducible Claim Cards for the Shadow-to-KOSIS handoff."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from clafact.claim_profile import ClaimProfile, build_claim_profile
from clafact.pipeline.parse import parse_claim
from clafact.pipeline.source_classify import classify


KOSIS_RETRIEVAL = "KOSIS_RETRIEVAL"


@dataclass(frozen=True)
class ClaimCard:
    """One reviewed numeric claim, independent of any selected KOSIS table."""

    sentence: str
    subject: str = ""
    topic: str = ""
    indicator: str = ""
    claim_value_raw: str = ""
    claim_value: float | None = None
    normalized_value: float | None = None
    unit: str = ""
    period: str = ""
    comparison: str = ""
    op: str = "eq"
    trend: str = ""
    region: str = ""
    population: str = ""
    source_type: str = ""
    claim_type: str = ""
    route: str = ""
    route_reason: str = ""
    context_inherited: bool = False
    quantity_count: int = 0
    reviewed: bool = False
    readiness: str = "needs_review"
    readiness_reasons: tuple[str, ...] = ()
    confirmed_at: str = ""

    @property
    def ready_for_kosis(self) -> bool:
        return self.readiness == "ready" and self.route == KOSIS_RETRIEVAL

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClaimCard":
        data = dict(payload)
        data["readiness_reasons"] = tuple(data.get("readiness_reasons") or ())
        return cls(**data)


def _readiness(
    *, route: str, indicator: str, claim_value_raw: str, period: str,
    quantity_count: int, reviewed: bool,
) -> tuple[str, tuple[str, ...]]:
    if route != KOSIS_RETRIEVAL:
        return "out_of_scope", ("KOSIS 조회 대상이 아닌 출처 경로",)
    reasons: list[str] = []
    if not indicator:
        reasons.append("지표 미확정")
    if not claim_value_raw:
        reasons.append("주장 수치 미확정")
    if not period:
        reasons.append("주장 시점 미확정")
    if quantity_count > 1 and not reviewed:
        reasons.append("복수 수치 — 검증할 주장값 선택 필요")
    if reasons:
        return "needs_review", tuple(reasons)
    return "ready", ()


def build_claim_card(
    sentence: str,
    article_date: str,
    *,
    previous_profile: ClaimProfile | None = None,
) -> ClaimCard:
    """Combine current rule outputs into an unconfirmed Claim Card draft."""
    profile = build_claim_profile(sentence, previous=previous_profile)
    parsed = parse_claim(sentence, article_date)
    source = classify(sentence)
    primary = parsed.quantities[0] if len(parsed.quantities) == 1 else None
    claim_value_raw = primary.raw if primary else ""
    unit = primary.unit if primary and primary.unit else profile.unit
    readiness, reasons = _readiness(
        route=source.route,
        indicator=profile.indicator,
        claim_value_raw=claim_value_raw,
        period=parsed.period,
        quantity_count=len(parsed.quantities),
        reviewed=False,
    )
    return ClaimCard(
        sentence=sentence,
        topic=profile.topic,
        indicator=profile.indicator,
        claim_value_raw=claim_value_raw,
        claim_value=primary.value if primary else None,
        normalized_value=primary.normalized_value if primary else None,
        unit=unit,
        period=parsed.period,
        comparison=profile.comparison,
        op=parsed.op,
        trend=parsed.trend,
        region=profile.region,
        population=profile.population,
        source_type=source.source_type,
        claim_type=source.claim_type,
        route=source.route,
        route_reason=source.reason,
        context_inherited=profile.context_inherited,
        quantity_count=len(parsed.quantities),
        readiness=readiness,
        readiness_reasons=reasons,
    )


def review_claim_card(
    card: ClaimCard,
    *,
    claim_value_raw: str | None = None,
    unit: str | None = None,
    period: str | None = None,
    indicator: str | None = None,
    topic: str | None = None,
    region: str | None = None,
    population: str | None = None,
    subject: str | None = None,
    confirmed_at: str = "",
) -> ClaimCard:
    """Apply a human's reviewed fields and recalculate KOSIS readiness."""
    updated = replace(
        card,
        claim_value_raw=(claim_value_raw if claim_value_raw is not None else card.claim_value_raw).strip(),
        unit=(unit if unit is not None else card.unit).strip(),
        period=(period if period is not None else card.period).strip(),
        indicator=(indicator if indicator is not None else card.indicator).strip(),
        topic=(topic if topic is not None else card.topic).strip(),
        region=(region if region is not None else card.region).strip(),
        population=(population if population is not None else card.population).strip(),
        subject=(subject if subject is not None else card.subject).strip(),
        reviewed=True,
        confirmed_at=confirmed_at or card.confirmed_at,
    )
    readiness, reasons = _readiness(
        route=updated.route,
        indicator=updated.indicator,
        claim_value_raw=updated.claim_value_raw,
        period=updated.period,
        quantity_count=updated.quantity_count,
        reviewed=True,
    )
    return replace(updated, readiness=readiness, readiness_reasons=reasons)


def claim_profile_from_card(card: ClaimCard) -> ClaimProfile:
    """Return the confirmed semantic fields consumed by candidate ranking."""
    return ClaimProfile(
        topic=card.topic,
        indicator=card.indicator,
        period=("월" if "-" in card.period and "Q" not in card.period else
                "분기" if "Q" in card.period else "연" if card.period else ""),
        comparison=card.comparison,
        unit=card.unit,
        region=card.region,
        population=card.population,
        search_query=card.indicator,
        context_inherited=card.context_inherited,
    )
