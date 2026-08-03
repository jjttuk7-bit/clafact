"""KOSIS 원본값으로 수치 주장 비교식을 재현하는 순수 계산 엔진."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class FormulaResult:
    status: str
    official_value: float | None
    reason: str


def _number(values: Mapping[str, object], name: str) -> float:
    return float(values[name])


def _series(values: Mapping[str, object]) -> list[float]:
    raw = values.get("series")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise ValueError("비교할 시계열 값이 없습니다.")
    return [float(value) for value in raw]


def _compare(claimed: float, official: float, tolerance: float) -> FormulaResult:
    if abs(claimed - official) <= tolerance:
        return FormulaResult("match", official, f"계산값 {official:g}이 허용오차 {tolerance:g} 안에서 일치합니다.")
    return FormulaResult("mismatch", official, f"주장값 {claimed:g}과 계산값 {official:g}의 차이가 허용오차를 넘습니다.")


def evaluate_formula(
    mode: str,
    *,
    claimed: float,
    values: Mapping[str, object],
    tolerance: float = 0.0,
) -> FormulaResult:
    """직접값·증감률·차이·비율·역사 극값·조건 개수를 동일한 규칙으로 비교한다."""
    try:
        if mode == "direct":
            official = _number(values, "value")
        elif mode == "change_rate":
            base, current = _number(values, "base"), _number(values, "current")
            if base == 0:
                raise ValueError("기준값이 0이어서 증감률을 계산할 수 없습니다.")
            official = (current / base - 1) * 100
        elif mode == "difference":
            official = _number(values, "left") - _number(values, "right")
        elif mode == "ratio":
            numerator, denominator = _number(values, "numerator"), _number(values, "denominator")
            if denominator == 0:
                raise ValueError("분모가 0이어서 비율을 계산할 수 없습니다.")
            official = numerator / denominator
        elif mode in {"historical_maximum", "historical_minimum"}:
            target, series = _number(values, "target"), _series(values)
            extreme = max(series) if mode == "historical_maximum" else min(series)
            if abs(target - extreme) > tolerance:
                return FormulaResult("mismatch", extreme, "주장 시점 값이 비교 기간의 극값이 아닙니다.")
            official = target
        elif mode == "count_lt_zero":
            official = float(sum(value < 0 for value in _series(values)))
        else:
            raise ValueError(f"지원하지 않는 비교식입니다: {mode}")
    except (KeyError, TypeError, ValueError) as error:
        return FormulaResult("not_comparable", None, str(error))
    return _compare(float(claimed), official, tolerance)
