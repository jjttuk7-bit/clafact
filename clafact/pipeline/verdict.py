"""판정 엔진 — 결정적(deterministic) 비교 로직. LLM 을 쓰지 않는다 (문서 03 설계 결정).

A2 규칙 라이브러리의 실행부: 단위 정규화, 반올림 허용, 파생 계산 재현.
새 규칙은 반드시 tests/ 에 테스트를 동반한다 — "테스트 없는 규칙은 등록 불가".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from clafact.schemas import Verdict, VerdictLabel, MismatchType

# 단위 → (정규화 계수, 계열). 계열이 다르면 비교 불가(UNVERIFIABLE).
UNIT_TABLE: dict[str, tuple[float, str]] = {
    "%": (1.0, "percent"),
    "퍼센트": (1.0, "percent"),
    "%p": (1.0, "percent_point"),  # %와 %p 는 다른 계열 — 혼동은 판정 불가/불일치 사유
    "포인트": (1.0, "percent_point"),
    "명": (1.0, "count"),
    "가구": (1.0, "count"),
    "건": (1.0, "count"),
    "천명": (1_000.0, "count"),
    "천가구": (1_000.0, "count"),
    "만명": (10_000.0, "count"),
    "만가구": (10_000.0, "count"),
    "억원": (100_000_000.0, "krw"),
    "조원": (1_000_000_000_000.0, "krw"),
    "원": (1.0, "krw"),
    "ha": (1.0, "area_ha"),
    "㎢": (100.0, "area_ha"),  # 1㎢ = 100ha
}

DEFAULT_REL_TOL = 0.005  # 상대 오차 0.5% — 골든셋으로 캘리브레이션 (문서 01 5.3)


def normalize(value: float, unit: str) -> tuple[float, str]:
    """단위 정규화. 미등록 단위는 그대로 두되 계열 'unknown'."""
    unit = (unit or "").strip()
    if unit in UNIT_TABLE:
        factor, family = UNIT_TABLE[unit]
        return value * factor, family
    return value, "unknown" if unit else "unitless"


def rounded_match(claimed: float, official: float) -> bool:
    """기사 수치가 반올림 값인 경우: 기사의 유효 소수 자릿수로
    공식 수치를 반올림했을 때 일치하면 반올림 일치로 본다.
    예: 기사 64.2 vs 공식 64.168... → round(64.168, 1) = 64.2 → 일치."""
    s = f"{claimed}"
    digits = len(s.split(".")[1]) if "." in s else 0
    return round(official, digits) == round(claimed, digits)


def derived_ratio(numerator_parts: Sequence[float], denominator: float) -> float:
    """파생 계산 재현: 구간 합산 ÷ 전체 (예: 65세 이상 4구간 ÷ 전체 농가)."""
    if denominator == 0:
        raise ZeroDivisionError("분모가 0")
    return sum(numerator_parts) / denominator


@dataclass
class CompareResult:
    verdict: Verdict
    claimed_norm: Optional[float] = None
    official_norm: Optional[float] = None


def _confidence(via_conversion: bool, rel: Optional[float], rel_tol: float) -> str:
    """신뢰도 그라데이션 (문서 12 §5.2, 규칙 A2-0004).

    - high:   단순 대조 (환산·임계 경유 없음, 오차가 허용치의 절반 이하)
    - medium: 파생 계산·단위 환산·임계 판정을 경유한 자동 판정 — 리뷰 우선
    - low:    허용 오차 경계 부근 (tol의 50% 초과) — 판정 보류급, 리뷰 최우선
    """
    if rel is not None and rel > rel_tol * 0.5:
        return "low"
    return "medium" if via_conversion else "high"


def compare(
    claimed: float,
    claimed_unit: str,
    official: float,
    official_unit: str,
    rel_tol: float = DEFAULT_REL_TOL,
    op: str = "eq",
) -> CompareResult:
    """주장 수치 vs 공식 수치 비교 → 판정.

    op: "eq"(같다) | "gte"(넘어섰다·이상·돌파) | "lte"(밑돌았다·이하·불과)
        — 규칙 A2-0001: 임계 표현은 등호가 아니라 부등호로 판정한다.
    순서: 단위 계열 확인 → 정규화 → (임계형) 부등호 → 반올림 일치 → 상대 오차.
    """
    c_val, c_fam = normalize(claimed, claimed_unit)
    o_val, o_fam = normalize(official, official_unit)
    c_factor = UNIT_TABLE.get((claimed_unit or "").strip(), (1.0, ""))[0]
    o_factor = UNIT_TABLE.get((official_unit or "").strip(), (1.0, ""))[0]
    # 환산·임계를 경유하면 medium 이하 (문서 12 §5.2)
    via_conversion = (c_factor != 1.0) or (o_factor != 1.0) or (op != "eq") \
        or ((claimed_unit or "").strip() != (official_unit or "").strip())

    # 1) 단위 계열 불일치 → 비교 불가 (% vs %p 혼동 포함)
    if c_fam != o_fam:
        if {c_fam, o_fam} == {"percent", "percent_point"}:
            return CompareResult(Verdict(
                label=VerdictLabel.MISMATCH,
                mismatch_type=MismatchType.VALUE,
                reason="%와 %p 혼동 — 서로 다른 지표 계열",
                calculation=f"claimed {claimed}{claimed_unit} vs official {official}{official_unit}",
                confidence="medium",
            ), c_val, o_val)
        return CompareResult(Verdict(
            label=VerdictLabel.UNVERIFIABLE,
            reason=f"단위 계열 불일치로 환산 불가: {claimed_unit or '무단위'} vs {official_unit or '무단위'}",
            calculation=f"family {c_fam} vs {o_fam}",
        ), c_val, o_val)

    # 2) 임계형 주장 (규칙 A2-0001): "넘어섰다"는 official ≥ claimed 면 일치
    if op in ("gte", "lte"):
        ok = (o_val >= c_val) if op == "gte" else (o_val <= c_val)
        sym = "≥" if op == "gte" else "≤"
        margin = abs(o_val - c_val) / max(abs(c_val), 1e-12)
        return CompareResult(Verdict(
            label=VerdictLabel.MATCH if ok else VerdictLabel.MISMATCH,
            mismatch_type=None if ok else MismatchType.VALUE,
            reason=f"임계형 판정: official {sym} claimed {'충족' if ok else '불충족'}",
            calculation=f"{o_val:.6g} {sym} {c_val:.6g}",
            confidence="low" if margin <= rel_tol * 2 else "medium",  # 경계 근접 시 리뷰 최우선
        ), c_val, o_val)

    # 3) 반올림 일치 (규칙 A2-0002): 반올림은 기사 단위 스케일 기준으로 판단
    #    예: 기사 "23만 명" vs 공식 230,028명 → 230028/10000=23.0028 → round=23 → 일치
    official_in_claimed_units = o_val / c_factor
    rel = abs(c_val - o_val) / max(abs(o_val), 1e-12)
    if rounded_match(claimed, official_in_claimed_units):
        return CompareResult(Verdict(
            label=VerdictLabel.MATCH,
            tolerance=rel_tol,
            reason="반올림 자릿수 기준 일치",
            calculation=f"{claimed}{claimed_unit} ≈ {official}{official_unit} (rounded)",
            confidence="medium" if via_conversion else "high",
        ), c_val, o_val)

    # 4) 상대 오차
    if rel <= rel_tol:
        return CompareResult(Verdict(
            label=VerdictLabel.MATCH,
            tolerance=rel_tol,
            reason=f"상대 오차 {rel:.4f} ≤ 허용 {rel_tol}",
            calculation=f"|{c_val}-{o_val}|/{o_val:.6g}={rel:.4f}",
            confidence=_confidence(via_conversion, rel, rel_tol),
        ), c_val, o_val)

    # 불일치: 허용치의 3배 이내면 경계 근접(low) — 오차가 클수록 확신은 높다
    mm_conf = "low" if rel <= rel_tol * 3 else ("medium" if via_conversion else "high")
    return CompareResult(Verdict(
        label=VerdictLabel.MISMATCH,
        mismatch_type=MismatchType.VALUE,
        tolerance=rel_tol,
        reason=f"상대 오차 {rel:.4f} > 허용 {rel_tol}",
        calculation=f"|{c_val}-{o_val}|/{o_val:.6g}={rel:.4f}",
        confidence=mm_conf,
    ), c_val, o_val)
