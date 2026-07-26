from dataclasses import dataclass
from typing import Any, Final, Iterable, Literal, Mapping


DisagreementType = Literal["P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR"]

P_PLUS_H_PLUS: Final[Literal["P+/H+"]] = "P+/H+"
P_PLUS_H_MINUS: Final[Literal["P+/H-"]] = "P+/H-"
P_MINUS_H_PLUS: Final[Literal["P-/H+"]] = "P-/H+"
P_MINUS_H_MINUS: Final[Literal["P-/H-"]] = "P-/H-"
HCX_ERROR: Final[Literal["HCX_ERROR"]] = "HCX_ERROR"
REVIEWED_METRIC_SCOPE_LABEL: Final[str] = "불일치 검토 표본 조건부 지표"


def classify_disagreement(
    python_candidate: bool,
    hcx_candidate: bool,
    hcx_status: str | None,
) -> DisagreementType:
    if hcx_status != "success":
        return HCX_ERROR
    if python_candidate:
        return P_PLUS_H_PLUS if hcx_candidate else P_PLUS_H_MINUS
    return P_MINUS_H_PLUS if hcx_candidate else P_MINUS_H_MINUS


@dataclass(frozen=True, slots=True)
class ConfusionMetrics:
    """Precision/recall inputs for one detector on an explicit sample."""

    tp: int
    fp: int
    fn: int
    tn: int
    evaluated_count: int
    precision: float | None
    recall: float | None

    def as_dict(self) -> dict[str, int | float | None]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "evaluated_count": self.evaluated_count,
            "precision": self.precision,
            "recall": self.recall,
        }


@dataclass(frozen=True, slots=True)
class ReviewedMetrics:
    """Human-reviewed detector metrics plus HCX response coverage."""

    python: ConfusionMetrics
    hcx: ConfusionMetrics
    python_or_hcx: ConfusionMetrics
    reviewed_count: int
    metric_scope_label: str
    independent_hcx_response_success: int
    independent_hcx_response_total: int
    independent_hcx_response_rate: float


def _confusion_metrics(observations: Iterable[tuple[bool, bool]]) -> ConfusionMetrics:
    tp = fp = fn = tn = 0
    for actual, predicted in observations:
        if actual and predicted:
            tp += 1
        elif not actual and predicted:
            fp += 1
        elif actual:
            fn += 1
        else:
            tn += 1

    evaluated_count = tp + fp + fn + tn
    precision_denominator = tp + fp
    recall_denominator = tp + fn
    return ConfusionMetrics(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        evaluated_count=evaluated_count,
        precision=tp / precision_denominator if precision_denominator else None,
        recall=tp / recall_denominator if recall_denominator else None,
    )


def compute_reviewed_metrics(
    rows: Iterable[Mapping[str, Any]],
) -> ReviewedMetrics:
    """Compute detector metrics only where a human supplied ground truth.

    ``true_candidate`` and ``false_positive`` are the only ground-truth labels.
    HCX failures are excluded from HCX precision/recall, while the OR detector
    fails open to the Python result. HCX response coverage is measured across
    every supplied sentence row so that a small HCX evaluation sample remains
    visible. Callers must supply rows from one experiment run; sentence rows do
    not carry provider/model/prompt metadata, so this pure function cannot verify
    that precondition. The current review workflow labels semantic disagreements,
    therefore these are conditional metrics, not whole-corpus performance.
    """

    supplied_rows = list(rows)
    reviewed_rows: list[tuple[Mapping[str, Any], bool]] = []
    for row in supplied_rows:
        label = row.get("human_label")
        if label == "true_candidate":
            reviewed_rows.append((row, True))
        elif label == "false_positive":
            reviewed_rows.append((row, False))

    python_observations = [
        (actual, bool(row["python_candidate"]))
        for row, actual in reviewed_rows
    ]
    hcx_observations = [
        (actual, bool(row["hcx_candidate"]))
        for row, actual in reviewed_rows
        if row.get("hcx_status") == "success"
    ]
    or_observations = [
        (
            actual,
            bool(row["python_candidate"])
            or (
                row.get("hcx_status") == "success"
                and bool(row["hcx_candidate"])
            ),
        )
        for row, actual in reviewed_rows
    ]

    response_total = len(supplied_rows)
    response_success = sum(
        row.get("hcx_status") == "success" for row in supplied_rows
    )
    return ReviewedMetrics(
        python=_confusion_metrics(python_observations),
        hcx=_confusion_metrics(hcx_observations),
        python_or_hcx=_confusion_metrics(or_observations),
        reviewed_count=len(reviewed_rows),
        metric_scope_label=REVIEWED_METRIC_SCOPE_LABEL,
        independent_hcx_response_success=response_success,
        independent_hcx_response_total=response_total,
        independent_hcx_response_rate=(
            response_success / response_total if response_total else 0.0
        ),
    )
