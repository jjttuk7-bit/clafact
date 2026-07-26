"""검증 실험실의 독립 실행 모드와 방식별 성능 측정."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from clafact.experiment_lab import ComparisonResult, ComparisonRow, Judge, _safe_judge
from clafact.pipeline import detect, source_classify
from clafact.pipeline.ingest import split_sentences
from clafact.pipeline.parse import parse_claim


@dataclass
class ModeRow:
    sentence: str
    candidate: bool | None
    reason: str
    quantities: list[str]
    parsed_period: str
    route: str
    claim_type: str


@dataclass
class ModeResult:
    rows: list[ModeRow]
    llm_calls: int
    elapsed_ms: int


def run_mode(text: str, article_date: str, mode: str, judge_fn: Judge | None = None) -> ModeResult:
    """한 방식을 독립 실행하고 문장별 탐지·판단 근거를 반환한다."""
    if mode not in {"python", "llm", "hybrid"}:
        raise ValueError(f"지원하지 않는 실험 모드: {mode}")

    started = perf_counter()
    rows: list[ModeRow] = []
    llm_calls = 0
    for sentence in split_sentences(text):
        parsed = parse_claim(sentence, article_date)
        classified = source_classify.classify(sentence)
        quantities = [quantity.raw for quantity in parsed.quantities]
        if mode == "python":
            candidate = detect.is_candidate(sentence)
            evidence = f"원문 수치: {' · '.join(quantities) or '-'} | 해석 시점: {parsed.period or '-'} | 주장 유형: {classified.claim_type} | 후속 라우팅 (사실 검증 아님): {classified.route}"
            if candidate:
                reason = f"후보 판정: 통과 | 적용 규칙: 수치 표현 + 변화/비교 서술 감지 | {evidence}"
            else:
                reason = f"후보 판정: 제외 | 적용 규칙 미충족: 수치 표현 또는 변화/비교 서술 없음 | {evidence}"
        elif mode == "llm":
            candidate, reason = _safe_judge(sentence, judge_fn) if judge_fn else (None, "LLM 호출 함수가 없습니다")
            llm_calls += 1
        else:
            python_candidate = detect.is_candidate(sentence)
            if not python_candidate:
                candidate = False
                reason = "Python 1차 후보가 아니므로 LLM 2차 판별 미호출"
            else:
                candidate, reason = _safe_judge(sentence, judge_fn) if judge_fn else (None, "LLM 호출 함수가 없습니다")
                llm_calls += 1
                if candidate is None:
                    candidate = True
                    reason = f"{reason} → Python 후보를 보수적 유지"
        rows.append(ModeRow(sentence, candidate, reason, quantities, parsed.period, classified.route, classified.claim_type))
    return ModeResult(rows, llm_calls, round((perf_counter() - started) * 1000))


def run_comparison(text: str, article_date: str, judge_fn: Judge | None = None) -> ComparisonResult:
    """세 방식을 독립 실행하고 방식별 시간과 판단 근거를 결합한다."""
    started = perf_counter()
    mode_results = {
        "python": run_mode(text, article_date, "python", judge_fn),
        "llm": run_mode(text, article_date, "llm", judge_fn),
        "hybrid": run_mode(text, article_date, "hybrid", judge_fn),
    }
    rows = []
    for python_row, llm_row, hybrid_row in zip(
        mode_results["python"].rows, mode_results["llm"].rows, mode_results["hybrid"].rows,
    ):
        rows.append(ComparisonRow(
            sentence=python_row.sentence,
            python_candidate=bool(python_row.candidate),
            llm_verifiable=llm_row.candidate,
            llm_reason=llm_row.reason,
            hybrid_candidate=bool(hybrid_row.candidate),
            hybrid_reason=hybrid_row.reason,
            quantities=python_row.quantities,
            parsed_period=python_row.parsed_period,
            route=python_row.route,
            claim_type=python_row.claim_type,
        ))
    total_elapsed = round((perf_counter() - started) * 1000)
    result = ComparisonResult(
        rows=rows,
        llm_calls=sum(item.llm_calls for item in mode_results.values()),
        elapsed_ms=max(total_elapsed, sum(item.elapsed_ms for item in mode_results.values())),
    )
    result.mode_results = mode_results
    return result
