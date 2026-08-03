from clafact.eval.comparison_formula import evaluate_formula


def test_direct_formula_matches_with_tolerance():
    result = evaluate_formula("direct", claimed=3.4, values={"value": 3.37}, tolerance=0.05)
    assert result.status == "match"
    assert result.official_value == 3.37


def test_change_rate_formula_calculates_two_period_rate():
    result = evaluate_formula("change_rate", claimed=3.4, values={"base": 106.09, "current": 109.67}, tolerance=0.05)
    assert result.status == "match"
    assert round(result.official_value, 3) == 3.374


def test_ratio_formula_calculates_derived_claim():
    result = evaluate_formula("ratio", claimed=2.4, values={"numerator": 7.5, "denominator": 3.1}, tolerance=0.05)
    assert result.status == "match"
    assert round(result.official_value, 2) == 2.42


def test_historical_maximum_checks_claimed_period_against_series():
    result = evaluate_formula("historical_maximum", claimed=9.193, values={"target": 9.193, "series": [8.708, 9.193, 4.2]})
    assert result.status == "match"


def test_count_condition_counts_negative_values():
    result = evaluate_formula("count_lt_zero", claimed=2, values={"series": [-1, 0, -2]})
    assert result.status == "match"
