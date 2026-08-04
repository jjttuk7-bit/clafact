"""Extract and validate exact KOSIS cell coordinates from returned API rows."""
from __future__ import annotations

from collections import OrderedDict
from typing import Mapping, Sequence


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def row_coordinate(row: Mapping[str, object]) -> dict[str, str]:
    """Return user-facing dimension labels and their exact values for one API row."""
    result: dict[str, str] = {}
    for level in range(1, 9):
        label = _clean(row.get(f"C{level}_OBJ_NM"))
        value = _clean(row.get(f"C{level}_NM"))
        if label and value:
            result[label] = value
    for label, field in (("항목", "ITM_NM"), ("시점", "PRD_DE"), ("단위", "UNIT_NM")):
        value = _clean(row.get(field))
        if value:
            result[label] = value
    return result


def extract_coordinate_axes(rows: Sequence[Mapping[str, object]]) -> dict[str, tuple[str, ...]]:
    """Return ordered, de-duplicated selectable values present in the official rows."""
    axes: OrderedDict[str, list[str]] = OrderedDict()
    for row in rows:
        for label, value in row_coordinate(row).items():
            axes.setdefault(label, [])
            if value not in axes[label]:
                axes[label].append(value)
    return {label: tuple(values) for label, values in axes.items()}


def _period_match(value: str, period: str) -> bool:
    return value.replace("-", "") == period.replace("-", "")


def recommend_coordinate_selection(
    axes: Mapping[str, Sequence[str]], *, subject: str = "", period: str = "", unit: str = "", comparison: str = "",
) -> dict[str, str]:
    """Recommend only values that exist in rows; callers still require human confirmation."""
    selection: dict[str, str] = {}
    for label, values in axes.items():
        cleaned_values = tuple(_clean(value) for value in values)
        if label == "시점" and period:
            match = next((value for value in cleaned_values if _period_match(value, period)), "")
        elif label == "단위" and unit:
            match = next((value for value in cleaned_values if value == _clean(unit)), "")
        elif label == "항목" and comparison:
            match = next((value for value in cleaned_values if _clean(comparison) in value), "")
        elif subject:
            match = next((value for value in cleaned_values if _clean(subject) == value), "")
        else:
            match = ""
        if match:
            selection[label] = match
    return selection


def matching_rows(rows: Sequence[Mapping[str, object]], selection: Mapping[str, str]) -> list[Mapping[str, object]]:
    """Return only official rows that match every selected coordinate."""
    return [
        row for row in rows
        if all(row_coordinate(row).get(_clean(label)) == _clean(value) for label, value in selection.items())
    ]
