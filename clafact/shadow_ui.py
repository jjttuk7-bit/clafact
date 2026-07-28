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
    if counts and set(counts) == {"success"}:
        return {"label": "HCX 응답 완료", "detail": f"HCX 상태: {detail}", "severity": "success"}
    if counts and set(counts) == {"not_configured"}:
        return {"label": "HCX 미설정 · AI 판정 미사용", "detail": f"HCX 상태: {detail}", "severity": "warning"}
    return {"label": "HCX 호출 오류·부분 실패 · 검토 필요", "detail": f"HCX 상태: {detail or '기록 없음'}", "severity": "error"}