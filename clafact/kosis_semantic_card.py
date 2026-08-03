"""Reusable seven-axis Semantic Cards for KOSIS table candidates."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from clafact.claim_profile import ClaimProfile
from clafact.kosis_candidate_search import KosisCandidate


@dataclass(frozen=True)
class SemanticCard:
    table_id: str
    org_id: str
    table_name: str
    topic: str
    indicator: str
    target_scope: str
    spatial: str
    time: str
    unit: str
    definition_formula: str
    field_status: dict[str, str]
    tag_source: str
    semantic_confidence: float
    confirmed_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SemanticCard":
        return cls(**{field: payload.get(field, "") for field in cls.__dataclass_fields__})


def build_semantic_card_draft(candidate: KosisCandidate, profile: ClaimProfile) -> SemanticCard:
    """Build a reviewable Card draft; callers must confirm it before persistence."""
    item = candidate.selected_item or profile.indicator
    status = {
        "topic": "inferred" if profile.topic else "unconfirmed",
        "indicator": "inferred" if item else "unconfirmed",
        "target_scope": "inferred" if profile.population else "unconfirmed",
        "spatial": "inferred" if profile.region else "unconfirmed",
        "time": "inferred" if profile.period else "unconfirmed",
        "unit": "inferred" if profile.unit else "unconfirmed",
        "definition_formula": "unconfirmed",
    }
    return SemanticCard(
        table_id=candidate.hit.tbl_id,
        org_id=candidate.hit.org_id,
        table_name=candidate.hit.tbl_name,
        topic=profile.topic,
        indicator=item,
        target_scope=profile.population,
        spatial=profile.region,
        time=profile.period,
        unit=profile.unit,
        definition_formula="",
        field_status=status,
        tag_source="claim_profile + KOSIS candidate metadata",
        semantic_confidence=round(candidate.fit_score / 100, 2),
    )


def semantic_card_review_model(
    card: SemanticCard, profile: ClaimProfile, *, reused: bool = False,
) -> dict[str, Any]:
    """Return a renderer-neutral Card model for human confirmation screens."""
    axes = {
        key: {"value": getattr(card, key), "status": card.field_status.get(key, "unconfirmed")}
        for key in ("topic", "indicator", "target_scope", "spatial", "time", "unit", "definition_formula")
    }
    return {
        "table_id": card.table_id,
        "org_id": card.org_id,
        "table_name": card.table_name,
        "axes": axes,
        "claim_context": {
            "topic": profile.topic,
            "indicator": profile.indicator,
            "region": profile.region,
            "population": profile.population,
            "period": profile.period,
            "unit": profile.unit,
            "comparison": profile.comparison,
        },
        "is_reused": reused,
    }
