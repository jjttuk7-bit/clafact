"""Convert KOSIS API rows to human-reviewed evidence input suggestions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence
from urllib.parse import parse_qs, urlparse


PERIOD_LABELS = {"A": "연", "Y": "연", "M": "월", "Q": "분기", "H": "반기"}


@dataclass(frozen=True)
class KosisTableIdentity:
    org_id: str
    table_id: str


@dataclass(frozen=True)
class KosisAutofillFields:
    title: str = ""
    organization: str = ""
    indicator: str = ""
    dimensions: str = ""
    time_dimension: str = ""
    unit: str = ""
    definition: str = ""
    source_selection: str = ""


def parse_kosis_table_identity(table_id: str, url: str) -> KosisTableIdentity:
    """Extract orgId/tblId from the original URL and validate manual table ID."""
    query = parse_qs(urlparse(url).query)
    org_id = query.get("orgId", [""])[0].strip()
    url_table_id = query.get("tblId", [""])[0].strip()
    if not org_id:
        raise ValueError("source URL must include orgId")
    if url_table_id and url_table_id != table_id.strip():
        raise ValueError("table_id does not match source URL tblId")
    if not table_id.strip():
        raise ValueError("table_id is required")
    return KosisTableIdentity(org_id=org_id, table_id=table_id.strip())


def _first_label(row: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def autofill_from_rows(*, table_id: str, rows: Sequence[Mapping[str, object]]) -> KosisAutofillFields:
    """Build a draft using explicit official API fields from the first response row."""
    del table_id
    if not rows:
        raise ValueError("KOSIS returned no rows for this table")
    row = rows[0]
    dimensions: list[str] = []
    selections: list[str] = []
    for level in range(1, 9):
        dimension = _first_label(row, f"C{level}_OBJ_NM")
        selection = _first_label(row, f"C{level}_NM")
        if dimension:
            dimensions.append(dimension)
            if selection:
                selections.append(f"{dimension}={selection}")
    period = _first_label(row, "PRD_SE")
    return KosisAutofillFields(
        title=_first_label(row, "TBL_NM"),
        organization=_first_label(row, "ORG_NM", "ORG_NAME"),
        indicator=_first_label(row, "ITM_NM"),
        dimensions=", ".join(dimensions),
        time_dimension=PERIOD_LABELS.get(period, period),
        unit=_first_label(row, "UNIT_NM"),
        definition="",
        source_selection=";".join(selections),
    )

def autofill_readiness_error(table_id: str, url: str) -> str | None:
    """Return a user-facing prerequisite message before an API autofill attempt."""
    if not table_id.strip():
        return "KOSIS 통계표 ID를 먼저 입력해 주세요."
    if not url.strip():
        return "원본 URL을 먼저 입력해 주세요."
    return None