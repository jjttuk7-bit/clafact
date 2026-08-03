"""Streamlit Shadow Mode가 사용하는 순수 UI 보조 함수."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def shadow_database_path(root: str | Path) -> Path:
    """운영 DB와 분리된 연구 전용 Shadow 데이터베이스 경로를 반환한다."""
    return Path(root) / "data" / "research" / "shadow_lab.db"


def validate_shadow_input(text: str) -> str | None:
    """실행 전 최소 입력 조건을 확인한다."""
    if not text.strip():
        return "분석할 기사 본문을 입력해 주세요."
    return None


def summary_metrics(summary: Mapping[str, Any]) -> dict[str, int]:
    """저장된 실행 요약을 안전한 표시용 정수로 정규화한다."""
    def number(key: str) -> int:
        try:
            return int(summary.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    return {
        "row_count": number("row_count"),
        "review_count": number("review_count"),
        "llm_calls": number("llm_calls"),
        "elapsed_ms": number("elapsed_ms"),
    }


def shadow_result_rows(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    """저장된 Shadow 실행을 Streamlit 표에 필요한 최소 열로 평탄화한다."""
    return [
        {
            "번호": row["row_index"],
            "문장": row["sentence"],
            "Python 후보": row["baseline"].get("python_candidate"),
            "LLM 후보": row["shadow"].get("llm_candidate"),
            "Hybrid 후보": row["shadow"].get("hybrid_candidate"),
            "위험 신호": " | ".join(row.get("risk_reasons", [])) or "-",
            "검토 상태": row["review_state"],
        }
        for row in run.get("rows", [])
    ]

def download_filenames(run_id: str) -> tuple[str, str]:
    """한 Shadow 실행의 JSON·CSV 기록 파일명을 반환한다."""
    return (f"{run_id}.json", f"{run_id}.csv")

def shadow_input_defaults(
    selected_article: Mapping[str, Any] | None, *, fallback_date: str
) -> dict[str, str] | None:
    """기존 비교 실험에서 선택한 CSV 기사를 Shadow 입력 기본값으로 변환한다."""
    if selected_article is None:
        return None
    return {
        "text": str(selected_article.get("body") or ""),
        "article_date": str(selected_article.get("date") or fallback_date),
        "title": str(selected_article.get("title") or "제목 없음"),
    }

def execution_status_summary(run: Mapping[str, Any]) -> dict[str, str]:
    """저장된 행의 HCX 상태를 사람이 해석 가능한 실행 상태로 집계한다."""
    counts: dict[str, int] = {}
    for row in run.get("rows", []):
        status = str(row.get("shadow", {}).get("hcx_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    detail = " · ".join(f"{status} {count}건" for status, count in sorted(counts.items()))
    response_rows = counts.get("success", 0)
    total_rows = sum(counts.values())
    if counts and set(counts) == {"success"}:
        return {"label": "HCX 응답 완료", "detail": f"HCX 상태: {detail}", "severity": "success", "response_rows": response_rows, "total_rows": total_rows}
    if counts and set(counts) == {"not_configured"}:
        return {"label": "HCX 미설정 · AI 판정 미사용", "detail": f"HCX 상태: {detail}", "severity": "warning", "response_rows": response_rows, "total_rows": total_rows}
    return {"label": "HCX 호출 오류·부분 실패 · 검토 필요", "detail": f"HCX 상태: {detail or '기록 없음'}", "severity": "error", "response_rows": response_rows, "total_rows": total_rows}

def llm_attempt_summary(run: Mapping[str, Any]) -> dict[str, int]:
    """Separate logical LLM comparison paths from successful HCX API responses."""
    metrics = summary_metrics(run.get("summary", {}))
    execution = execution_status_summary(run)
    return {
        "attempt_paths": metrics["llm_calls"],
        "actual_responses": int(execution["response_rows"]),
        "total_rows": int(execution["total_rows"]),
    }

def _record_value(record: Mapping[str, Any] | object, key: str) -> Any:
    if isinstance(record, Mapping):
        return record.get(key)
    return None


def _snapshot_values(record: Mapping[str, Any] | object) -> set[str]:
    values: set[str] = set()
    snapshot_ids = _record_value(record, "snapshot_ids")
    if isinstance(snapshot_ids, (list, tuple, set)):
        values.update(str(value).strip() for value in snapshot_ids if str(value).strip())
    snapshot_id = str(_record_value(record, "snapshot_id") or "").strip()
    if snapshot_id:
        values.update(part.strip() for part in snapshot_id.split("|") if part.strip())
    return values



def semantic_card_catalog_summary(
    cards: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...], *,
    current_run_confirmed_table_ids: tuple[str, ...] | list[str] = (),
    reused_table_ids: tuple[str, ...] | list[str] = (),
    pending_count: int = 0,
) -> dict[str, int]:
    """Return clear growth-Catalog metrics without coupling UI helpers to SQLite."""
    confirmed = {str(card.get("table_id") or "").strip() for card in cards}
    confirmed.discard("")
    current = {str(table_id).strip() for table_id in current_run_confirmed_table_ids}
    reused = {str(table_id).strip() for table_id in reused_table_ids}
    return {
        "catalog_card_count": len(confirmed),
        "current_run_new_card_count": len(current - reused),
        "current_run_reused_card_count": len(current & reused),
        "pending_card_count": max(0, int(pending_count)),
    }

def current_semantic_summary(
    run: Mapping[str, Any], *, candidate_searches: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    mappings: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    comparisons: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    completed_claims: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> dict[str, int]:
    """Aggregate persisted research records for the current Shadow run."""
    candidate_rows = {
        int(row["row_index"])
        for row in run.get("rows", [])
        if isinstance(row, Mapping)
        and (bool(_record_value(_record_value(row, "baseline") or {}, "python_candidate"))
             or bool(_record_value(_record_value(row, "shadow") or {}, "llm_candidate"))
             or bool(_record_value(_record_value(row, "shadow") or {}, "hybrid_candidate")))
    }
    searched_rows = {
        int(_record_value(search, "row_index"))
        for search in candidate_searches
        if str(_record_value(search, "row_index") or "").strip().isdigit()
    }
    reviewed_mappings = [
        mapping for mapping in mappings
        if str(_record_value(mapping, "status") or "").strip() == "reviewed"
    ]
    snapshots = set().union(*(_snapshot_values(comparison) for comparison in comparisons)) if comparisons else set()
    verdicts = [str(_record_value(comparison, "status") or "").strip() for comparison in comparisons]
    return {
        "candidate_sentence_count": len(candidate_rows),
        "candidate_search_count": len(searched_rows),
        "mapped_table_count": len(reviewed_mappings),
        "evidence_snapshot_count": len(snapshots),
        "comparison_count": len(comparisons),
        "match_count": verdicts.count("match"),
        "mismatch_count": verdicts.count("mismatch"),
        "unverifiable_count": verdicts.count("unverifiable"),
        "completed_claim_count": len(completed_claims),
    }


def e2e_semantic_summary(verdicts: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> dict[str, int]:
    """Summarize persisted Golden Set E2E verdicts by candidate, not component."""
    candidates: dict[str, dict[str, Any]] = {}
    for position, verdict in enumerate(verdicts):
        candidate_key = str(_record_value(verdict, "candidate_id") or _record_value(verdict, "sentence") or f"record-{position}").strip()
        candidate = candidates.setdefault(candidate_key, {"verdicts": set(), "snapshots": set()})
        status = str(_record_value(verdict, "verdict") or "").strip()
        if status in {"match", "mismatch", "unverifiable"}:
            candidate["verdicts"].add(status)
        candidate["snapshots"].update(_snapshot_values(verdict))

    counts = {"match": 0, "mismatch": 0, "unverifiable": 0}
    final_count = 0
    evidence_backed_count = 0
    for candidate in candidates.values():
        statuses = candidate["verdicts"]
        if candidate["snapshots"]:
            evidence_backed_count += 1
        if not statuses:
            continue
        final_count += 1
        if "mismatch" in statuses:
            counts["mismatch"] += 1
        elif "match" in statuses:
            counts["match"] += 1
        else:
            counts["unverifiable"] += 1
    return {
        "candidate_count": len(candidates),
        "final_count": final_count,
        "match_count": counts["match"],
        "mismatch_count": counts["mismatch"],
        "unverifiable_count": counts["unverifiable"],
        "evidence_backed_count": evidence_backed_count,
    }