from collections import Counter

import pytest

from clafact.experiment_analysis import (
    HCX_ERROR,
    P_MINUS_H_MINUS,
    P_MINUS_H_PLUS,
    P_PLUS_H_MINUS,
    P_PLUS_H_PLUS,
    classify_disagreement,
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


@pytest.mark.parametrize("hcx_status", ["error", "timeout", "parse_error", None])
def test_hcx_failure_is_never_conflated_with_h_minus(hcx_status: str | None) -> None:
    assert classify_disagreement(True, False, hcx_status) == HCX_ERROR
    assert classify_disagreement(False, False, hcx_status) == HCX_ERROR


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
