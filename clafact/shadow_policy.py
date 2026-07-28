"""Shadow Lab 연구 실행에 적용하는 안전 정책."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_CLAIM_TYPES = frozenset({
    "absolute_value",
    "change",
    "growth_rate",
    "ratio",
    "ranking",
})
ALLOWED_VERDICTS = frozenset({
    "supported",
    "refuted",
    "partially_supported",
    "insufficient_evidence",
    "out_of_scope",
})
DEFAULT_REVIEW_WHEN = (
    "required_slot_missing",
    "candidate_conflict",
    "definition_mismatch",
    "unit_or_time_ambiguous",
)


@dataclass(frozen=True)
class ShadowPolicy:
    domain: str = "population"
    evidence_source: str = "KOSIS"
    claim_types: tuple[str, ...] = (
        "absolute_value",
        "change",
        "growth_rate",
        "ratio",
        "ranking",
    )
    default_when_uncertain: str = "insufficient_evidence"
    review_when: tuple[str, ...] = DEFAULT_REVIEW_WHEN
    version: str = "shadow-policy-v1"

    def __post_init__(self) -> None:
        unknown_claim_types = set(self.claim_types) - ALLOWED_CLAIM_TYPES
        if unknown_claim_types:
            raise ValueError(f"unknown claim type: {sorted(unknown_claim_types)}")
        if self.default_when_uncertain not in ALLOWED_VERDICTS:
            raise ValueError(
                f"unknown default verdict: {self.default_when_uncertain}"
            )
        if not self.domain.strip():
            raise ValueError("domain must not be blank")
        if not self.evidence_source.strip():
            raise ValueError("evidence_source must not be blank")
        if not self.review_when:
            raise ValueError("review_when must not be empty")

    @classmethod
    def default(cls) -> "ShadowPolicy":
        return cls()

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "evidence_source": self.evidence_source,
            "claim_types": list(self.claim_types),
            "default_when_uncertain": self.default_when_uncertain,
            "review_when": list(self.review_when),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ShadowPolicy":
        return cls(
            domain=str(payload.get("domain", "population")),
            evidence_source=str(payload.get("evidence_source", "KOSIS")),
            claim_types=tuple(payload.get("claim_types", cls().claim_types)),
            default_when_uncertain=str(
                payload.get("default_when_uncertain", "insufficient_evidence")
            ),
            review_when=tuple(payload.get("review_when", DEFAULT_REVIEW_WHEN)),
            version=str(payload.get("version", "shadow-policy-v1")),
        )
