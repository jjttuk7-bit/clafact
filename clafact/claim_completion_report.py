"""Build a portable report from independently reproducible Claim completions."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from clafact.claim_completion import complete_claim_case


def complete_claim_cases(cases: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    """Return completed Claim records in the caller-supplied order."""
    return [complete_claim_case(**dict(case)).as_dict() for case in cases]
