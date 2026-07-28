"""Evaluate whether a KOSIS evidence object is applicable to a claim sentence."""
from __future__ import annotations

import re
from dataclasses import dataclass

from clafact.kosis_evidence import KosisEvidenceObject


KNOWN_UNITS = ("%", "퍼센트", "명", "원", "건", "가구", "세대", "곳", "호")


@dataclass(frozen=True)
class KosisClaimMatch:
    score: int
    status: str
    reasons: tuple[str, ...]
    score_breakdown: tuple[str, ...] = ()


def _contains_indicator(sentence: str, indicator: str) -> bool:
    compact_sentence = re.sub(r"\s+", "", sentence)
    compact_indicator = re.sub(r"\s+", "", indicator)
    return bool(compact_indicator and compact_indicator in compact_sentence)


def _semantic_indicator_label(sentence: str, indicator: str) -> str:
    claim = re.sub(r"\s+", "", sentence)
    normalized_indicator = re.sub(r"\s+", "", indicator)
    if "전년동월" in normalized_indicator and any(
        phrase in claim for phrase in ("지난해같은달", "전년동월", "전년동월대비")
    ):
        return "전년동월비"
    if "전월비" in normalized_indicator and any(
        phrase in claim for phrase in ("전월대비", "지난달대비")
    ):
        return "전월비"
    return ""


def _sentence_unit(sentence: str) -> str:
    for unit in KNOWN_UNITS:
        if unit in sentence:
            return unit
    return ""


def _time_matches(sentence: str, time_dimension: str) -> bool:
    if re.search(r"\d{4}년", sentence):
        return time_dimension == "연"
    if re.search(r"\d{1,2}월", sentence) or any(token in sentence for token in ("지난달", "이번달")):
        return time_dimension == "월"
    if "분기" in sentence:
        return time_dimension == "분기"
    return False


def evaluate_claim_evidence_match(sentence: str, evidence: KosisEvidenceObject) -> KosisClaimMatch:
    """Score applicability, not truth; each result preserves its explicit evidence."""
    score = 0
    reasons: list[str] = []
    score_breakdown: list[str] = []
    conflicts = False

    if _contains_indicator(sentence, evidence.indicator):
        score += 40
        reasons.append("지표명 직접 일치")
        score_breakdown.append("+40 지표명 직접 일치")
    else:
        semantic_label = _semantic_indicator_label(sentence, evidence.indicator)
        if semantic_label:
            score += 40
            reasons.append(f"지표 의미 일치: 문장 표현 → {semantic_label}")
            score_breakdown.append(f"+40 지표 의미 일치 ({semantic_label})")
        else:
            reasons.append("지표명 직접 일치 미확인")

    sentence_unit = _sentence_unit(sentence)
    if sentence_unit:
        if sentence_unit == evidence.unit:
            score += 25
            reasons.append("단위 일치")
            score_breakdown.append(f"+25 단위 일치 ({evidence.unit})")
        else:
            conflicts = True
            reasons.append("단위 충돌")
            reasons.append(f"단위 충돌 상세: 문장 {sentence_unit}, 통계표 {evidence.unit}")
    else:
        reasons.append("문장 단위 미확인")

    if _time_matches(sentence, evidence.time_dimension):
        score += 20
        reasons.append("시간 주기 일치")
        score_breakdown.append(f"+20 시간 주기 일치 ({evidence.time_dimension})")
    else:
        reasons.append("시간 주기 직접 일치 미확인")

    selected_values = {
        value for value in evidence.source_selection.values()
        if value and value not in {"계", "전체"}
    }
    if selected_values:
        if all(value in sentence for value in selected_values):
            score += 15
            reasons.append("선택 조건 명시 일치")
            score_breakdown.append("+15 선택 조건 명시 일치")
        else:
            reasons.append("선택 조건 직접 일치 미확인")
    else:
        reasons.append("비교 가능한 선택 조건 없음")

    status = "high" if score >= 80 and not conflicts else "needs_review"
    return KosisClaimMatch(
        score=score,
        status=status,
        reasons=tuple(reasons),
        score_breakdown=tuple(score_breakdown),
    )