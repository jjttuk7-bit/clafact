"""Claim/Evidence/Verdict 스키마와 상태 머신.

문서 10(워크플로우 정의서) 1장의 상태 머신을 코드로 구현한다.
모든 모듈은 이 상태 코드를 공용한다 — 용어가 갈라지면 여기를 고친다.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class State(str, Enum):
    DETECTED = "DETECTED"
    PARSED = "PARSED"
    MAPPED = "MAPPED"
    EVIDENCED = "EVIDENCED"
    VERDICTED = "VERDICTED"
    EXPLAINED = "EXPLAINED"
    IN_REVIEW = "IN_REVIEW"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"
    UNVERIFIABLE = "UNVERIFIABLE"


# 정상 경로 전이표. UNVERIFIABLE 은 어느 상태에서든 진입 가능(사유 필수).
TRANSITIONS: dict[State, set[State]] = {
    State.DETECTED: {State.PARSED},
    State.PARSED: {State.MAPPED},
    State.MAPPED: {State.EVIDENCED},
    State.EVIDENCED: {State.VERDICTED},
    State.VERDICTED: {State.EXPLAINED},
    State.EXPLAINED: {State.IN_REVIEW},
    State.IN_REVIEW: {State.CONFIRMED, State.CORRECTED, State.REJECTED},
    State.REJECTED: {State.PARSED},  # 반려 → 재처리
}

TERMINAL = {State.CONFIRMED, State.CORRECTED, State.UNVERIFIABLE}


class ClaimType(str, Enum):
    INCREASE_DECREASE = "increase_decrease"  # 증감
    SCALE = "scale"                          # 규모
    COMPARISON = "comparison"                # 비교
    FORECAST = "forecast"                    # 전망(검증 제외)


class VerdictLabel(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNVERIFIABLE = "unverifiable"


class MismatchType(str, Enum):
    VALUE = "value"
    PERIOD = "period"
    POPULATION = "population"
    EXAGGERATION = "exaggeration"


@dataclass
class Claim:
    sentence: str
    article_id: str = ""
    sentence_id: str = ""
    claim_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    claim_type: Optional[ClaimType] = None
    metric: str = ""
    period: str = ""
    unit: str = ""
    population: str = ""
    value: Optional[float] = None
    verifiable: bool = True
    state: State = State.DETECTED
    state_log: list[dict] = field(default_factory=list)

    def transition(self, new: State, reason: str = "") -> None:
        """상태 전이. 불법 전이는 예외, UNVERIFIABLE 은 사유 필수."""
        if new == State.UNVERIFIABLE:
            if not reason:
                raise ValueError("UNVERIFIABLE 전이에는 사유 코드가 필수입니다 (문서 10 원칙)")
        elif self.state in TERMINAL:
            raise ValueError(f"종료 상태 {self.state}에서 전이 불가")
        elif new not in TRANSITIONS.get(self.state, set()):
            raise ValueError(f"불법 전이: {self.state} → {new}")
        self.state_log.append({"ts": time.time(), "from": self.state.value, "to": new.value, "reason": reason})
        self.state = new


@dataclass
class Evidence:
    tbl_id: str = ""
    org_id: str = ""
    tbl_name: str = ""
    query_params: dict = field(default_factory=dict)
    value: Optional[float] = None
    unit: str = ""
    period: str = ""
    source_note: str = ""


@dataclass
class Verdict:
    label: VerdictLabel
    mismatch_type: Optional[MismatchType] = None
    calculation: str = ""
    tolerance: float = 0.0
    reason: str = ""
    explanation: str = ""
    # 신뢰도 그라데이션 (문서 12 §5.2): high / medium / low, 판단불가는 None.
    # 리뷰 큐 정렬: 불일치 → low → medium → high (WF-2 개정)
    confidence: Optional[str] = None


def as_dict(obj: Any) -> dict:
    """dataclass → JSON 직렬화 가능 dict (Enum 은 value 로)."""
    from dataclasses import asdict
    d = asdict(obj)

    def clean(v):
        if isinstance(v, Enum):
            return v.value
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x) for x in v]
        return v

    return {k: clean(v) for k, v in d.items()}
