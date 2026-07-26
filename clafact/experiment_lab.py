"""검증 실험실 비교 엔진의 호환 진입점."""
from clafact.experiment_modes import run_comparison, run_mode
from clafact.experiment_types import (
    ComparisonResult,
    ComparisonRow,
    Judge,
    JudgeResult,
)

__all__ = [
    "ComparisonResult",
    "ComparisonRow",
    "Judge",
    "JudgeResult",
    "run_comparison",
    "run_mode",
]
