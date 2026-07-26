"""검증 실험실 EDA의 파일·범위·세션 상태 규칙."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import MutableMapping


MAX_EDA_ROWS = 1000

EDA_FILE_SIGNATURE_KEY = "experiment_eda_file_signature"
EDA_CACHE_KEY = "experiment_eda_cache_key"
EDA_RANGE_KEY = "experiment_eda_range"
EDA_RANGE_START_KEY = "experiment_eda_range_start"
EDA_RANGE_END_KEY = "experiment_eda_range_end"
EDA_REPORT_KEY = "experiment_eda_report"
EDA_VIEW_KEY = "experiment_eda_view"
EDA_SELECTED_ARTICLE_KEY = "experiment_eda_selected_article"
EDA_FILTER_STATE_KEYS = (
    "experiment_eda_filter_quality",
    "experiment_eda_filter_body",
    "experiment_eda_filter_min_candidates",
    "experiment_eda_filter_max_candidates",
)

_INVALIDATED_KEYS = (
    EDA_CACHE_KEY,
    EDA_RANGE_KEY,
    EDA_RANGE_START_KEY,
    EDA_RANGE_END_KEY,
    EDA_REPORT_KEY,
    EDA_VIEW_KEY,
    EDA_SELECTED_ARTICLE_KEY,
    *EDA_FILTER_STATE_KEYS,
)


@dataclass(frozen=True)
class EdaRange:
    """1부터 시작하는 원본 행 범위. ``end``는 화면에서는 포함 값이다."""

    start: int
    end: int

    @property
    def span(self) -> int:
        return self.end - self.start + 1

    @property
    def slice_bounds(self) -> tuple[int, int]:
        """Python 슬라이스의 0-based start, exclusive end."""

        return self.start - 1, self.end


def payload_signature(payload: bytes) -> str:
    """원본 바이트를 보관하지 않고 파일 정체성만 계산한다."""

    return hashlib.sha256(payload).hexdigest()


def resolve_eda_range(
    total_rows: int,
    requested: EdaRange | None = None,
    *,
    confirmed: bool = False,
) -> EdaRange | None:
    """작은 파일은 전체, 큰 파일은 명시적으로 확정된 최대 1,000행만 반환한다."""

    if total_rows < 0:
        raise ValueError("전체 행 수는 음수일 수 없습니다.")
    if total_rows <= MAX_EDA_ROWS:
        return EdaRange(1, total_rows) if total_rows else None
    if not confirmed:
        return None
    if requested is None:
        raise ValueError("분석 범위를 선택해 주세요.")
    if (
        requested.start < 1
        or requested.end < requested.start
        or requested.end > total_rows
        or requested.span > MAX_EDA_ROWS
    ):
        raise ValueError("분석 범위는 원본 안의 연속된 최대 1,000행이어야 합니다.")
    return requested


def cache_key(signature: str, selected: EdaRange) -> tuple[str, int, int]:
    return signature, selected.start, selected.end


def invalidate_for_payload(
    state: MutableMapping[str, object],
    signature: str,
) -> bool:
    """새 파일이면 EDA 파생 상태만 제거하고 서명만 저장한다."""

    if state.get(EDA_FILE_SIGNATURE_KEY) == signature:
        return False
    for key in _INVALIDATED_KEYS:
        state.pop(key, None)
    state[EDA_FILE_SIGNATURE_KEY] = signature
    return True
