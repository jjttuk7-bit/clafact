"""검증 실험실의 독립 실행 모드와 방식별 성능 측정."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from time import perf_counter

from clafact.experiment_analysis import classify_disagreement
from clafact.experiment_lab import ComparisonResult, ComparisonRow, Judge
from clafact.pipeline.detect_llm import HcxDecision
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
    evidence_status: str = "not_applicable"
    evidence_reason: str = ""
    quoted_spans: list[str] | None = None
    hcx_status: str = "not_run"


@dataclass
class ModeResult:
    rows: list[ModeRow]
    llm_calls: int
    elapsed_ms: int


def _safe_hcx_decision(sentence: str, judge_fn: Judge | None) -> tuple[HcxDecision, str]:
    if judge_fn is None:
        return (
            HcxDecision(None, "HCX 호출 함수가 없습니다", "unknown", "HCX가 설정되지 않았습니다", []),
            "not_configured",
        )
    try:
        result = judge_fn(sentence)
    except Exception as error:
        return (
            HcxDecision(None, f"HCX 호출 실패: {error}", "unknown", "호출 실패로 근거 상태를 알 수 없습니다", []),
            "call_error",
        )
    if isinstance(result, HcxDecision):
        if isinstance(result.candidate, bool):
            return result, "success"
        reason = f"{result.candidate_reason} {result.evidence_reason}"
        status = "parse_error" if "파싱" in reason or "JSON" in reason else "invalid_response"
        return HcxDecision(
            None,
            result.candidate_reason,
            result.evidence_status,
            result.evidence_reason,
            result.quoted_spans,
        ), status
    try:
        candidate, reason = result
    except (TypeError, ValueError):
        return (
            HcxDecision(None, "빈 HCX 응답", "unknown", "후보 판정 결과가 없습니다", []),
            "empty_response" if result is None else "invalid_response",
        )
    status = "success" if isinstance(candidate, bool) else "invalid_response"
    normalized_candidate = candidate if status == "success" else None
    decision = HcxDecision(
        normalized_candidate,
        reason,
        "unknown",
        "기존 판정 함수는 근거 상태를 제공하지 않습니다",
        [],
    )
    return decision, status


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
        hcx_decision = HcxDecision(None, "해당 방식에서 HCX 미실행", "not_applicable", "HCX 미실행", [])
        hcx_status = "not_run"
        if mode == "python":
            candidate = detect.is_candidate(sentence)
            evidence = f"원문 수치: {' · '.join(quantities) or '-'} | 해석 시점: {parsed.period or '-'} | 주장 유형: {classified.claim_type} | 후속 라우팅 (사실 검증 아님): {classified.route}"
            if candidate:
                reason = f"후보 판정: 통과 | 적용 규칙: 수치 표현 + 변화/비교 서술 감지 | {evidence}"
            else:
                reason = f"후보 판정: 제외 | 적용 규칙 미충족: 수치 표현 또는 변화/비교 서술 없음 | {evidence}"
        elif mode == "llm":
            hcx_decision, hcx_status = _safe_hcx_decision(sentence, judge_fn)
            candidate = hcx_decision.candidate
            reason = hcx_decision.candidate_reason
            llm_calls += 1
        else:
            python_candidate = detect.is_candidate(sentence)
            if not python_candidate:
                candidate = False
                reason = "Python 1차 후보가 아니므로 LLM 2차 판별 미호출"
            else:
                hcx_decision, hcx_status = _safe_hcx_decision(sentence, judge_fn)
                candidate = hcx_decision.candidate
                reason = hcx_decision.candidate_reason
                llm_calls += 1
                if hcx_status != "success":
                    candidate = True
                    reason = f"{reason} → Python 후보를 보수적 유지"
        rows.append(ModeRow(
            sentence, candidate, reason, quantities, parsed.period, classified.route, classified.claim_type,
            hcx_decision.evidence_status, hcx_decision.evidence_reason, hcx_decision.quoted_spans, hcx_status,
        ))
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
            hcx_evidence_status=llm_row.evidence_status,
            hcx_evidence_reason=llm_row.evidence_reason,
            hcx_quoted_spans=llm_row.quoted_spans,
            hcx_status=llm_row.hcx_status,
            disagreement_class=classify_disagreement(
                bool(python_row.candidate), bool(llm_row.candidate), llm_row.hcx_status,
            ),
        ))
    total_elapsed = round((perf_counter() - started) * 1000)
    result = ComparisonResult(
        rows=rows,
        llm_calls=sum(item.llm_calls for item in mode_results.values()),
        elapsed_ms=max(total_elapsed, sum(item.elapsed_ms for item in mode_results.values())),
        disagreement_counts=dict(Counter(row.disagreement_class for row in rows)),
    )
    result.mode_results = mode_results
    return result
