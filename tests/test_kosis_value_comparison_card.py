import pytest

from clafact.kosis_value_comparison import KosisValueComparison
from clafact.kosis_value_comparison_card import build_value_comparison_card


def _comparison(*, status="match", official_value="2.4%", official_period="2025-10"):
    return KosisValueComparison(
        status=status,
        reason="비교 결과",
        claim_value="2.4%",
        official_value=official_value,
        claim_period="2025-10",
        official_period=official_period,
        snapshot_id="kosis-snapshot-1",
        snapshot_retrieved_at="2026-07-29T10:00:00+09:00",
        tolerance=0.05,
        gate_results=(),
    )


def _snapshot(records):
    return {"records": records}


def _record(*, period="2025.10", value="2.4", unit="%", indicator="전년동월비(%)", selection=None):
    return {
        "period": period,
        "value": value,
        "unit": unit,
        "indicator": indicator,
        "selection": selection or {"지수종류": "총지수"},
    }


def test_builds_primary_card_with_compared_official_record_first():
    card = build_value_comparison_card(
        _comparison(),
        _snapshot([
            _record(value="9.9", indicator="전월비(%)"),
            _record(),
            _record(value="2.4", period="2025.09"),
        ]),
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
    )

    assert card.primary is not None
    assert card.primary.official_value == "2.4%"
    assert card.primary.period == "2025-10"
    assert [candidate.period for candidate in card.alternatives] == ["2025-10", "2025-09"]


def test_orders_alternatives_by_period_indicator_selection_and_unit_compatibility():
    card = build_value_comparison_card(
        _comparison(),
        _snapshot([
            _record(value="2.4"),
            _record(value="1.0", selection={"지수종류": "다른지수"}),
            _record(value="1.0", indicator="전월비(%)"),
            _record(value="1.0", unit="명"),
            _record(value="1.0", period="2025.09"),
        ]),
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
    )

    assert [candidate.unit for candidate in card.alternatives] == ["명", "%", "%", "%"]
    assert [candidate.indicator for candidate in card.alternatives] == ["전년동월비(%)", "전년동월비(%)", "전월비(%)", "전년동월비(%)"]
    assert [candidate.match_score for candidate in card.alternatives] == [3, 3, 3, 3]


def test_not_comparable_and_empty_snapshot_have_no_false_primary():
    comparison = _comparison(status="not_comparable", official_value="", official_period="")

    card = build_value_comparison_card(
        comparison,
        _snapshot([]),
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
    )

    assert card.primary is None
    assert card.alternatives == ()
    assert card.reason == "비교 결과"


def test_primary_ignores_same_value_record_when_indicator_or_selection_differs():
    card = build_value_comparison_card(
        _comparison(),
        _snapshot([
            _record(indicator="전월비(%)"),
            _record(selection={"지수종류": "다른지수"}),
            _record(),
        ]),
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
    )

    assert card.primary is not None
    assert card.primary.indicator == "전년동월비(%)"
    assert dict(card.primary.selection) == {"지수종류": "총지수"}

def test_card_freezes_gate_results_for_read_only_rendering():
    comparison = _comparison()
    comparison = KosisValueComparison(
        **{**comparison.__dict__, "gate_results": ({"name": "기간", "passed": True, "detail": "일치"},)}
    )

    card = build_value_comparison_card(
        comparison,
        _snapshot([_record()]),
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
    )

    with pytest.raises(TypeError):
        card.gate_results[0]["passed"] = False


def test_orders_tied_alternatives_independently_of_api_input_order():
    primary = _record(value="2.4")
    first = _record(value="9.0")
    second = _record(value="1.0")

    first_card = build_value_comparison_card(
        _comparison(),
        _snapshot([primary, first, second]),
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
    )
    second_card = build_value_comparison_card(
        _comparison(),
        _snapshot([primary, second, first]),
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
    )

    assert [candidate.official_value for candidate in first_card.alternatives] == ["1.0%", "9.0%"]
    assert [candidate.official_value for candidate in second_card.alternatives] == ["1.0%", "9.0%"]