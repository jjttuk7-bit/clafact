"""검증 실험실 EDA 준비 상태를 Streamlit과 분리한다."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Mapping, Sequence

from clafact.experiment_eda import EdaReport, analyze_rows
from clafact.experiment_eda_view import EdaView, build_eda_view


EMPTY_CSV_MESSAGE = "CSV에 분석할 데이터 행이 없습니다."
EdaPreparationStatus = Literal["empty", "ready"]
AnalyzeRows = Callable[..., EdaReport]
BuildView = Callable[[EdaReport], EdaView]


@dataclass(frozen=True)
class EdaPreparation:
    status: EdaPreparationStatus
    report: EdaReport | None
    view: EdaView | None
    user_message: str


def prepare_eda(
    rows: Sequence[Mapping[str, object]],
    *,
    row_number_start: int = 1,
    analyze_fn: AnalyzeRows = analyze_rows,
    view_fn: BuildView = build_eda_view,
) -> EdaPreparation:
    """선택된 CSV 행을 Python EDA 보고서와 렌더링 뷰로 준비한다."""

    if not rows:
        return EdaPreparation(
            status="empty",
            report=None,
            view=None,
            user_message=EMPTY_CSV_MESSAGE,
        )
    report = analyze_fn(rows, row_number_start=row_number_start)
    return EdaPreparation(
        status="ready",
        report=report,
        view=view_fn(report),
        user_message="",
    )