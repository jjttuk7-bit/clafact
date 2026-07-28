"""Convert manual KOSIS evidence input to a research evidence object."""
from __future__ import annotations

from clafact.kosis_evidence import KosisEvidenceObject


def build_manual_evidence(*, table_id: str, url: str, title: str, organization: str,
                          indicator: str, dimensions: str, time_dimension: str,
                          unit: str, definition: str, source_selection: str,
                          retrieved_at: str, structure_type: str = "") -> KosisEvidenceObject:
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
        table_id=table_id, url=url, title=title, organization=organization,
        indicator=indicator, dimensions=parsed_dimensions, time_dimension=time_dimension,
        unit=unit, definition=definition, source_selection=parsed_selection,
        retrieved_at=retrieved_at, structure_type=structure_type,
    )