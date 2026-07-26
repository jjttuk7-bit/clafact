from collections import Counter
from typing import Final, Literal, get_args, get_origin

import pytest

from clafact import experiment_analysis
from clafact.experiment_analysis import (
    HCX_ERROR,
    P_MINUS_H_MINUS,
    P_MINUS_H_PLUS,
    P_PLUS_H_MINUS,
    P_PLUS_H_PLUS,
    classify_disagreement,
    compute_reviewed_metrics,
)


@pytest.mark.parametrize(
    ("python_candidate", "hcx_candidate", "hcx_status", "expected"),
    [
        (True, True, "success", P_PLUS_H_PLUS),
        (True, False, "success", P_PLUS_H_MINUS),
        (False, True, "success", P_MINUS_H_PLUS),
        (False, False, "success", P_MINUS_H_MINUS),
    ],
)
def test_classifies_successful_semantic_results(
    python_candidate: bool,
    hcx_candidate: bool,
    hcx_status: str,
    expected: str,
) -> None:
    assert (
        classify_disagreement(python_candidate, hcx_candidate, hcx_status)
        == expected
    )


@pytest.mark.parametrize("python_candidate", [False, True])
@pytest.mark.parametrize("hcx_candidate", [False, True])
@pytest.mark.parametrize("hcx_status", ["error", "timeout", "parse_error", None])
def test_hcx_failure_always_takes_priority(
    python_candidate: bool,
    hcx_candidate: bool,
    hcx_status: str | None,
) -> None:
    assert (
        classify_disagreement(python_candidate, hcx_candidate, hcx_status)
        == HCX_ERROR
    )


def test_bucket_constants_keep_precise_literal_types() -> None:
    expected = {
        "P_PLUS_H_PLUS": P_PLUS_H_PLUS,
        "P_PLUS_H_MINUS": P_PLUS_H_MINUS,
        "P_MINUS_H_PLUS": P_MINUS_H_PLUS,
        "P_MINUS_H_MINUS": P_MINUS_H_MINUS,
        "HCX_ERROR": HCX_ERROR,
    }

    for name, value in expected.items():
        annotation = experiment_analysis.__annotations__[name]
        assert get_origin(annotation) is Final
        literal_type = get_args(annotation)[0]
        assert get_origin(literal_type) is Literal
        assert get_args(literal_type) == (value,)


def test_each_sentence_contributes_to_exactly_one_bucket() -> None:
    observations = [
        (True, True, "success"),
        (True, False, "success"),
        (False, True, "success"),
        (False, False, "success"),
        (True, False, "timeout"),
    ]

    counts = Counter(classify_disagreement(*observation) for observation in observations)

    assert set(counts) == {
        P_PLUS_H_PLUS,
        P_PLUS_H_MINUS,
        P_MINUS_H_PLUS,
        P_MINUS_H_MINUS,
        HCX_ERROR,
    }
    assert sum(counts.values()) == len(observations)


def test_reviewed_metrics_exclude_unreviewed_and_hold_rows() -> None:
    rows = [
        {
            "human_label": "true_candidate",
            "python_candidate": True,
            "hcx_status": "success",
            "hcx_candidate": True,
        },
        {
            "human_label": "true_candidate",
            "python_candidate": False,
            "hcx_status": "success",
            "hcx_candidate": True,
        },
        {
            "human_label": "false_positive",
            "python_candidate": True,
            "hcx_status": "success",
            "hcx_candidate": False,
        },
        {
            "human_label": "false_positive",
            "python_candidate": False,
            "hcx_status": "timeout",
            "hcx_candidate": None,
        },
        {
            "human_label": "hold",
            "python_candidate": True,
            "hcx_status": "success",
            "hcx_candidate": True,
        },
        {
            "human_label": None,
            "python_candidate": True,
            "hcx_status": "success",
            "hcx_candidate": True,
        },
    ]

    result = compute_reviewed_metrics(rows)

    assert result.reviewed_count == 4
    assert result.python.as_dict() == {
        "tp": 1,
        "fp": 1,
        "fn": 1,
        "tn": 1,
        "evaluated_count": 4,
        "precision": 0.5,
        "recall": 0.5,
    }
    assert result.hcx.as_dict() == {
        "tp": 2,
        "fp": 0,
        "fn": 0,
        "tn": 1,
        "evaluated_count": 3,
        "precision": 1.0,
        "recall": 1.0,
    }
    assert result.python_or_hcx.as_dict() == {
        "tp": 2,
        "fp": 1,
        "fn": 0,
        "tn": 1,
        "evaluated_count": 4,
        "precision": pytest.approx(2 / 3),
        "recall": 1.0,
    }
    assert result.hcx_response_success == 5
    assert result.hcx_response_total == 6
    assert result.hcx_response_rate == pytest.approx(5 / 6)


def test_hcx_error_is_excluded_from_hcx_metrics_and_or_fails_open_to_python() -> None:
    rows = [
        {
            "human_label": "true_candidate",
            "python_candidate": True,
            "hcx_status": "parse_error",
            "hcx_candidate": None,
        },
        {
            "human_label": "true_candidate",
            "python_candidate": False,
            "hcx_status": "timeout",
            "hcx_candidate": None,
        },
    ]

    result = compute_reviewed_metrics(rows)

    assert result.hcx.evaluated_count == 0
    assert result.python_or_hcx.tp == 1
    assert result.python_or_hcx.fn == 1
    assert result.python_or_hcx.evaluated_count == 2
    assert result.hcx_response_success == 0
    assert result.hcx_response_total == 2
    assert result.hcx_response_rate == 0.0


def test_reviewed_metrics_use_zero_for_empty_precision_and_recall_denominators() -> None:
    result = compute_reviewed_metrics(
        [
            {
                "human_label": "false_positive",
                "python_candidate": False,
                "hcx_status": "success",
                "hcx_candidate": False,
            }
        ]
    )

    for metrics in (result.python, result.hcx, result.python_or_hcx):
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.tn == 1
        assert metrics.evaluated_count == 1


def test_empty_input_has_explicit_zero_sample_sizes() -> None:
    result = compute_reviewed_metrics([])

    assert result.reviewed_count == 0
    assert result.python.evaluated_count == 0
    assert result.hcx.evaluated_count == 0
    assert result.python_or_hcx.evaluated_count == 0
    assert result.hcx_response_success == 0
    assert result.hcx_response_total == 0
    assert result.hcx_response_rate == 0.0
