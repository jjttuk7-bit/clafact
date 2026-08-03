"""Conservative extraction of independent item-and-quantity Claims from one sentence."""
from __future__ import annotations

from dataclasses import dataclass
import re

from clafact.pipeline.parse import extract_quantities


_ITEM_WITH_PARENTHESIZED_VALUE = re.compile(
    r"(?P<subject>[가-힣][가-힣·\s]{0,30}?)\s*\((?P<quantity>[^()]+)\)"
)


@dataclass(frozen=True)
class AtomicClaim:
    """One independently verifiable item-and-value pair from a parent sentence."""

    claim_index: int
    subject: str
    value_raw: str
    unit: str
    source_span: tuple[int, int]


def extract_atomic_claims(sentence: str) -> tuple[AtomicClaim, ...]:
    """Extract repeated ``품목명(수치)`` pairs only when two or more are unambiguous.

    A single pair remains on the existing one-sentence/one-Claim path. This avoids
    expanding ordinary parenthetical context into a false independent Claim.
    """
    found: list[AtomicClaim] = []
    for match in _ITEM_WITH_PARENTHESIZED_VALUE.finditer(sentence):
        quantities = extract_quantities(match.group("quantity"))
        if len(quantities) != 1:
            continue
        quantity = quantities[0]
        if not quantity.unit:
            continue
        found.append(AtomicClaim(
            claim_index=len(found) + 1,
            subject=" ".join(match.group("subject").split()),
            value_raw=quantity.raw,
            unit=quantity.unit,
            source_span=match.span(),
        ))
    return tuple(found) if len(found) >= 2 else ()
