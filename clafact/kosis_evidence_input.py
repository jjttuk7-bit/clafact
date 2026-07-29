"""Convert manual KOSIS evidence input to a research evidence object."""
from __future__ import annotations

from typing import Mapping

from clafact.kosis_evidence import KosisEvidenceObject
from clafact.kosis_organization import normalize_kosis_organization

def build_candidate_evidence_prefill(*, table_id: str, org_id: str, title: str, indicator: str) -> dict[str, str]:
    """Build the complete evidence-form draft for a selected KOSIS candidate."""
    return {
        "table_id": table_id,
        "url": f"https://kosis.kr/statHtml/statHtml.do?orgId={org_id}&tblId={table_id}",
        "title": title.strip(),
        "indicator": indicator.strip(),
    }


def build_manual_evidence(*, table_id: str, url: str, title: str, organization: str,
                          indicator: str, dimensions: str, time_dimension: str,
                          unit: str, definition: str, source_selection: str,
                          retrieved_at: str, structure_type: str = "", snapshot_id: str = "",
                          definition_provenance: Mapping[str, str] | None = None) -> KosisEvidenceObject:
    parsed_dimensions = tuple(item.strip() for item in dimensions.split(",") if item.strip())
    parsed_selection = {}
    for item in source_selection.split(";"):
        if not item.strip():
            continue
        key, separator, value = item.partition("=")
        if not separator or not key.strip() or not value.strip():
            raise ValueError("source_selection must use key=value")
        parsed_selection[key.strip()] = value.strip()
    return KosisEvidenceObject(
        table_id=table_id, url=url, title=title, organization=normalize_kosis_organization(organization),
        indicator=indicator, dimensions=parsed_dimensions, time_dimension=time_dimension,
        unit=unit, definition=definition, source_selection=parsed_selection,
        retrieved_at=retrieved_at, structure_type=structure_type, snapshot_id=snapshot_id,
        definition_provenance=dict(definition_provenance or {}),
    )