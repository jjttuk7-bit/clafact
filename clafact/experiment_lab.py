"""운영 저장소와 분리된 수치 주장 탐지 방식 비교 엔진."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from clafact.pipeline import detect, source_classify
from clafact.pipeline.detect_llm import judge
from clafact.pipeline.ingest import split_sentences
from clafact.pipeline.parse import parse_claim

Judge = Callable[[str], tuple[bool, str]]


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


@dataclass
class ComparisonResult:
    rows: list[ComparisonRow]
    llm_calls: int
    elapsed_ms: int


def _safe_judge(sentence: str, judge_fn: Judge) -> tuple[bool | None, str]:
    try:
        return judge_fn(sentence)
    except Exception as error:
        return None, f"LLM 호출 실패: {error}"


def run_comparison(text: str, article_date: str, judge_fn: Judge | None = None) -> ComparisonResult:
    """세 탐지 방식을 비교한다. Store/KOSIS/운영 큐를 호출하지 않는다."""
    started = perf_counter()
    judge_fn = judge_fn or judge
    rows: list[ComparisonRow] = []
    llm_calls = 0

    for sentence in split_sentences(text):
        python_candidate = detect.is_candidate(sentence)
        llm_verifiable, llm_reason = _safe_judge(sentence, judge_fn)
        llm_calls += 1

        if python_candidate:
            hybrid_signal, hybrid_reason = _safe_judge(sentence, judge_fn)
            llm_calls += 1
            hybrid_candidate = True if hybrid_signal is None else hybrid_signal
            if hybrid_signal is None:
                hybrid_reason = f"{hybrid_reason} → Python 후보를 보수적 유지"
        else:
            hybrid_candidate = False
            hybrid_reason = "Python 1차 후보가 아니므로 LLM 2차 판별 미호출"

        parsed = parse_claim(sentence, article_date)
        classified = source_classify.classify(sentence)
        rows.append(ComparisonRow(
            sentence=sentence,
            python_candidate=python_candidate,
            llm_verifiable=llm_verifiable,
            llm_reason=llm_reason,
            hybrid_candidate=hybrid_candidate,
            hybrid_reason=hybrid_reason,
            quantities=[quantity.raw for quantity in parsed.quantities],
            parsed_period=parsed.period,
            route=classified.route,
            claim_type=classified.claim_type,
        ))

    return ComparisonResult(
        rows=rows,
        llm_calls=llm_calls,
        elapsed_ms=round((perf_counter() - started) * 1000),
    )

from clafact.experiment_modes import run_comparison, run_mode
