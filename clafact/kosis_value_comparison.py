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
        }


def _compact(value: object) -> str:
    return re.sub(r"[\s()_%]", "", str(value or "")).lower()


def _normalize_period(value: object) -> str:
    period = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})[.-](\d{1,2})", period)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
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


def _result(
    *,
    status: str,
    reason: str,
    quantity: Quantity | None,
    claim_period: str,
    snapshot: Mapping[str, object],
    record: Mapping[str, object] | None = None,
    tolerance: float | None = None,
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
    if quantity is None:
        return _result(
            status="not_comparable",
            reason="문장에서 비교할 수치를 추출하지 못했습니다.",
            quantity=None,
            claim_period=parsed.period,
            snapshot=snapshot or {},
        )
    if not parsed.period:
        return _result(
            status="not_comparable",
            reason="문장의 기준 기간을 특정하지 못했습니다.",
            quantity=quantity,
            claim_period="",
            snapshot=snapshot or {},
        )
    if not snapshot or not snapshot.get("records"):
        return _result(
            status="not_comparable",
            reason="연결된 KOSIS 조회 스냅샷이 없습니다.",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot or {},
        )

    period_records = [
        record for record in snapshot["records"]
        if isinstance(record, Mapping) and _normalize_period(record.get("period")) == parsed.period
    ]
    if not period_records:
        return _result(
            status="not_comparable",
            reason=f"스냅샷에 문장 기간({parsed.period})의 값이 없습니다.",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
        )

    indicator_records = [
        record for record in period_records
        if _compact(record.get("indicator")) == _compact(evidence_indicator)
    ]
    if not indicator_records:
        return _result(
            status="not_comparable",
            reason="스냅샷에 선택한 핵심 지표와 같은 항목이 없습니다.",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
        )

    selected_records = [
        record for record in indicator_records
        if _matches_selection(record, evidence_selection)
    ]
    if not selected_records:
        return _result(
            status="not_comparable",
            reason="스냅샷에 근거 객체의 선택 조건과 같은 값이 없습니다.",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
        )

    record = selected_records[0]
    official_unit = str(record.get("unit", "")).strip()
    if quantity.unit in {"%", "퍼센트"} and official_unit != "%":
        return _result(
            status="not_comparable",
            reason=f"단위가 다릅니다: 문장 {quantity.unit}, KOSIS {official_unit or '-'}",
            quantity=quantity,
            claim_period=parsed.period,
            snapshot=snapshot,
            record=record,
        )
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
        )
    return _result(
        status="mismatch",
        reason=f"문장 값과 KOSIS 값의 차이는 {difference:.2f}{'%p' if quantity.unit in {'%', '퍼센트'} else ''}입니다.",
        quantity=quantity,
        claim_period=parsed.period,
        snapshot=snapshot,
        record=record,
        tolerance=tolerance,
    )
