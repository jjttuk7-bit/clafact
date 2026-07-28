"""Explainable KOSIS table structure classification."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


REGION_DIMENSION_TOKENS = ("지역", "시도", "시군구", "행정구역", "시군", "읍면동")


@dataclass(frozen=True)
class KosisTableStructure:
    structure_type: str
    reason: str
    observed_dimensions: tuple[str, ...]


def _value(row: Mapping[str, object], key: str) -> str:
    return str(row.get(key, "")).strip()


def classify_table_structure(rows: Sequence[Mapping[str, object]]) -> KosisTableStructure:
    """Classify visible table shape from API row variation, preserving the reason."""
    if not rows:
        return KosisTableStructure("unknown", "API 응답 행이 없어 구조를 판정할 수 없습니다.", ())

    dimensions: dict[str, set[str]] = {}
    for level in range(1, 9):
        names = {_value(row, f"C{level}_OBJ_NM") for row in rows}
        names.discard("")
        if not names:
            continue
        name = sorted(names)[0]
        values = {_value(row, f"C{level}_NM") for row in rows}
        values.discard("")
        dimensions[name] = values

    varying_dimensions = {
        name: values for name, values in dimensions.items() if len(values) > 1
    }
    periods = {_value(row, "PRD_DE") for row in rows}
    periods.discard("")
    indicators = {_value(row, "ITM_NM") for row in rows}
    indicators.discard("")

    observed_dimensions = tuple(dimensions)
    regional = [
        name for name, values in varying_dimensions.items()
        if any(token in name for token in REGION_DIMENSION_TOKENS) and len(values) > 1
    ]
    if regional:
        return KosisTableStructure(
            "regional_comparison",
            f"{regional[0]} 차원의 값이 {len(varying_dimensions[regional[0]])}개로 변해 지역 비교 구조입니다.",
            observed_dimensions,
        )
    if len(varying_dimensions) >= 2:
        names = ", ".join(varying_dimensions)
        return KosisTableStructure(
            "crosstab",
            f"{names} 등 {len(varying_dimensions)}개 분류 차원이 함께 변해 교차표 구조입니다.",
            observed_dimensions,
        )
    if len(periods) > 1 and len(indicators) <= 1:
        return KosisTableStructure(
            "time_series",
            f"시간 값이 {len(periods)}개로 변하고 지표는 하나여서 시계열 구조입니다.",
            observed_dimensions,
        )
    if len(indicators) > 1:
        return KosisTableStructure(
            "indicator_bundle",
            f"지표 항목이 {len(indicators)}개로 함께 제공되어 지표 묶음 구조입니다.",
            observed_dimensions,
        )
    return KosisTableStructure(
        "unknown",
        "관찰된 행만으로는 대표 구조를 확정할 수 없습니다.",
        observed_dimensions,
    )
