"""Canonical display names for KOSIS statistical authorities."""
from __future__ import annotations


CURRENT_NATIONAL_DATA_AGENCY = "국가데이터처"
_LEGACY_NATIONAL_DATA_AGENCY_NAMES = frozenset({"통계청", "statistics korea", "kostat"})


def normalize_kosis_organization(organization: str) -> str:
    """Use the current agency name while preserving unrelated authorities."""
    normalized = organization.strip()
    if normalized.lower() in _LEGACY_NATIONAL_DATA_AGENCY_NAMES:
        return CURRENT_NATIONAL_DATA_AGENCY
    return normalized
