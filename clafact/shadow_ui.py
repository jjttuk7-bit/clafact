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