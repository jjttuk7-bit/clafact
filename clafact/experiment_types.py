"""검증 실험실 비교 엔진이 공유하는 중립 타입."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from clafact.pipeline.detect_llm import HcxDecision

JudgeResult = HcxDecision | tuple[bool, str]
Judge = Callable[[str], JudgeResult]


@dataclass
class ComparisonRow:
    sentence: str
    python_candidate: bool
    llm_verifiable: bool | None
    llm_reason: str
    hybrid_candidate: bool
    hybrid_reason: str
    quantities: list[str]
    parsed_period: str
    route: str
    claim_type: str
    hcx_evidence_status: str = "unknown"
    hcx_evidence_reason: str = ""
    hcx_quoted_spans: list[str] | None = None
    hcx_status: str = "not_run"
    disagreement_class: str = "HCX_ERROR"


@dataclass
class ComparisonResult:
    rows: list[ComparisonRow]
    llm_calls: int
    elapsed_ms: int
    disagreement_counts: dict[str, int] = field(default_factory=dict)
