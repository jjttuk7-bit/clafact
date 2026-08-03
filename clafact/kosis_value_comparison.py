"""Compare one numeric Shadow claim against a saved KOSIS response snapshot."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from clafact.pipeline.parse import Quantity, parse_claim


PERCENT_TOLERANCE = 0.05


@dataclass(frozen=True)
class KosisValueComparison:
    """Research-only numerical comparison with explicit source and reasoning."""

    status: str
    reason: str
    claim_value: str
    official_value: str
    claim_period: str
    official_period: str
    snapshot_id: str
    snapshot_retrieved_at: str
    tolerance: float | None
    gate_results: tuple[dict[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "claim_value": self.claim_value,
            "official_value": self.official_value,
            "claim_period": self.claim_period,
            "official_period": self.official_period,
            "snapshot_id": self.snapshot_id,
            "snapshot_retrieved_at": self.snapshot_retrieved_at,
            "tolerance": self.tolerance,
            "gate_results": [dict(gate) for gate in self.gate_results],
        }


def _compact(value: object) -> str:
    return re.sub(r"[\s()_%]", "", str(value or "")).lower()


def _normalize_period(value: object) -> str:
    period = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})[.-](\d{1,2})", period)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
    compact_month = re.fullmatch(r"(\d{4})(\d{2})", period)
    if compact_month:
        return f"{compact_month.group(1)}-{compact_month.group(2)}"
    return period.replace(".", "-")


def _select_quantity(quantities: list[Quantity]) -> Quantity | None:
    percentages = [quantity for quantity in quantities if quantity.unit in {"%", "퍼센트"}]
    return percentages[0] if percentages else (quantities[0] if quantities else None)


def _formatted_quantity(quantity: Quantity) -> str:
    return quantity.raw or f"{quantity.value:g}{quantity.unit}"


def _matches_selection(record: Mapping[str, object], selection: Mapping[str, str]) -> bool:
    record_selection = record.get("selection") or {}
    if not isinstance(record_selection, Mapping):
        return False
    for dimension, value in selection.items():
        if value and str(record_selection.get(dimension, "")).strip() != str(value).strip():
            return False
    return True


def _gate(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"name": name, "passed": passed, "detail": detail}


def _value_kind(unit: object) -> str:
    normalized = str(unit or "").strip().lower()
    if normalized in {"%p", "퍼센트포인트"}:
        return "퍼센트포인트"
    if normalized in {"%", "퍼센트"}:
        return "비율"
    return "절대수치"


def _normalized_unit(unit: object) -> str:
    normalized = str(unit or "").strip().lower()
    return {"퍼센트": "%", "퍼센트포인트": "%p"}.get(normalized, normalized)


def _result(
    *,
    status: str,
    reason: str,
    quantity: Quantity | None,
    claim_period: str,
    snapshot: Mapping[str, object],
    record: Mapping[str, object] | None = None,
    tolerance: float | None = None,
    gate_results: list[dict[str, object]] | None = None,
) -> KosisValueComparison:
    return KosisValueComparison(
        status=status,
        reason=reason,
        claim_value=_formatted_quantity(quantity) if quantity else "",
        official_value=(f"{record.get('value', '')}{record.get('unit', '')}" if record else ""),
        claim_period=claim_period,
        official_period=_normalize_period(record.get("period", "")) if record else "",
        snapshot_id=str(snapshot.get("snapshot_id", "")),
        snapshot_retrieved_at=str(snapshot.get("retrieved_at", "")),
        tolerance=tolerance,
        gate_results=tuple(gate_results or ()),
    )


def compare_claim_to_snapshot(
    *,
    claim_sentence: str,
    article_date: str,
    evidence_indicator: str,
    evidence_selection: Mapping[str, str],
    snapshot: Mapping[str, object] | None,
) -> KosisValueComparison:
    """Compare a parsed claim only with a stored, explicit KOSIS snapshot."""
    parsed = parse_claim(claim_sentence, article_date)
    quantity = _select_quantity(parsed.quantities)
    gates: list[dict[str, object]] = []
    if quantity is None:
        return _result(
            status="not_comparable",
            reason="문장에서 비교할 수치를 추출하지 못했습니다.",
            quantity=None,
            claim_period=parsed.period,
            snapshot=snapshot or {},
            gate_results=gates,
        )
    if not parsed.period:
        gates.append(_gate("기간", False, "문장의 기준 기간을 특정하지 못했습니다."))
        return _result(
            status="not_comparable",
            reason="문장의 기준 기간을 특정하지 못했습니다.",
            quantity=quantity,
            claim_period="",
            snapshot=snapshot or {},
            gate_results=gates,
        )
    if not snapshot or not snapshot.get("records"):
        return _result(
            status="not_comparable",
            reason="연결된 KOSIS 조회 스냅샷이 없습니다.",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot or {},
            gate_results=gates,
        )

    period_records = [
        record for record in snapshot["records"]
        if isinstance(record, Mapping) and _normalize_period(record.get("period")) == parsed.period
    ]
    if not period_records:
        reason = f"스냅샷에 문장 기간({parsed.period})의 값이 없습니다."
        gates.append(_gate("기간", False, reason))
        return _result(
            status="not_comparable",
            reason=reason,
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            gate_results=gates,
        )
    gates.append(_gate("기간", True, f"문장과 스냅샷 기간이 {parsed.period}로 일치합니다."))

    indicator_records = [
        record for record in period_records
        if _compact(record.get("indicator")) == _compact(evidence_indicator)
    ]
    if not indicator_records:
        reason = "스냅샷에 선택한 핵심 지표와 같은 항목이 없습니다."
        gates.append(_gate("지표", False, reason))
        return _result(
            status="not_comparable",
            reason=reason,
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            gate_results=gates,
        )
    gates.append(_gate("지표", True, f"핵심 지표 {evidence_indicator}가 일치합니다."))

    selected_records = [
        record for record in indicator_records
        if _matches_selection(record, evidence_selection)
    ]
    if not selected_records:
        reason = "스냅샷에 근거 객체의 선택 조건과 같은 값이 없습니다."
        gates.append(_gate("선택 조건", False, reason))
        return _result(
            status="not_comparable",
            reason=reason,
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            gate_results=gates,
        )
    gates.append(_gate("선택 조건", True, "근거 객체의 선택 조건이 스냅샷과 일치합니다."))

    record = selected_records[0]
    official_unit = str(record.get("unit", "")).strip()
    claim_kind = _value_kind(quantity.unit)
    official_kind = _value_kind(official_unit)
    if claim_kind != official_kind:
        reason = f"값 성격이 다릅니다: 문장 {claim_kind}, KOSIS {official_kind}"
        gates.append(_gate("값 성격", False, reason))
        return _result(
            status="not_comparable",
            reason=reason,
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            record=record,
            gate_results=gates,
        )
    gates.append(_gate("값 성격", True, f"문장과 KOSIS 값 성격이 {claim_kind}로 일치합니다."))

    if _normalized_unit(quantity.unit) != _normalized_unit(official_unit):
        reason = f"단위가 다릅니다: 문장 {quantity.unit or '-'}, KOSIS {official_unit or '-'}"
        gates.append(_gate("단위", False, reason))
        return _result(
            status="not_comparable",
            reason=reason,
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            record=record,
            gate_results=gates,
        )
    gates.append(_gate("단위", True, f"문장과 KOSIS 단위가 {_normalized_unit(official_unit) or '-'}로 일치합니다."))
    try:
        official_value = float(str(record.get("value", "")).replace(",", ""))
    except ValueError:
        return _result(
            status="not_comparable",
            reason="KOSIS 스냅샷 값을 수치로 해석하지 못했습니다.",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            record=record,
            gate_results=gates,
        )

    tolerance = PERCENT_TOLERANCE if quantity.unit in {"%", "퍼센트"} else 0.0
    difference = abs(quantity.normalized_value - official_value)
    if difference <= tolerance:
        return _result(
            status="match",
            reason=f"문장 값과 KOSIS 값이 허용 오차 {tolerance:g}{'%p' if tolerance else ''} 안에서 일치합니다.",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            record=record,
            tolerance=tolerance,
            gate_results=gates,
        )
    return _result(
        status="mismatch",
        reason=f"문장 값과 KOSIS 값의 차이는 {difference:.2f}{'%p' if quantity.unit in {'%', '퍼센트'} else ''}입니다.",
        quantity=quantity,
        claim_period=parsed.period,
        snapshot=snapshot,
        record=record,
        tolerance=tolerance,
        gate_results=gates,
    )