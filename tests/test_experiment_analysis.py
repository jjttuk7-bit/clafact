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
