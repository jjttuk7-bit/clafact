from clafact.kosis_value_comparison import compare_claim_to_snapshot


def _snapshot(records):
    return {
        "snapshot_id": "kosis-snapshot-1",
        "retrieved_at": "2026-07-29T10:00:00+09:00",
        "records": records,
    }


def _record(*, period="2025.10", value="2.4", unit="%", indicator="전년동월비(%)", selection=None):
    return {
        "period": period,
        "value": value,
        "unit": unit,
        "indicator": indicator,
        "selection": selection or {"지수종류": "총지수"},
    }


def test_compares_percent_claim_against_same_period_snapshot_value():
    result = compare_claim_to_snapshot(
        claim_sentence="지난달 소비자 물가가 지난해 같은 달 대비 2.4% 상승했다.",
        article_date="2025-11-04",
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
        snapshot=_snapshot([_record()]),
    )

    assert result.status == "match"
    assert result.claim_value == "2.4%"
    assert result.official_value == "2.4%"
    assert result.snapshot_id == "kosis-snapshot-1"
    assert [gate["name"] for gate in result.gate_results[:3]] == ["기간", "지표", "선택 조건"]
    assert all(gate["passed"] for gate in result.gate_results[:3])


def test_marks_different_value_as_mismatch_when_comparison_is_possible():
    result = compare_claim_to_snapshot(
        claim_sentence="지난달 소비자 물가가 지난해 같은 달 대비 2.6% 상승했다.",
        article_date="2025-11-04",
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
        snapshot=_snapshot([_record(value="2.4")]),
    )

    assert result.status == "mismatch"
    assert "0.20%p" in result.reason


def test_does_not_guess_when_snapshot_period_is_not_present():
    result = compare_claim_to_snapshot(
        claim_sentence="지난달 소비자 물가가 지난해 같은 달 대비 2.4% 상승했다.",
        article_date="2025-11-04",
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
        snapshot=_snapshot([_record(period="2025.09")]),
    )

    assert result.status == "not_comparable"
    assert "기간" in result.reason


def test_requires_same_selected_indicator_when_snapshot_contains_multiple_items():
    result = compare_claim_to_snapshot(
        claim_sentence="지난달 소비자 물가가 지난해 같은 달 대비 2.4% 상승했다.",
        article_date="2025-11-04",
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
        snapshot=_snapshot([_record(indicator="전월비(%)")]),
    )

    assert result.status == "not_comparable"
    assert "지표" in result.reason


def test_does_not_compare_percentage_point_to_percent_rate():
    result = compare_claim_to_snapshot(
        claim_sentence="지난달 소비자 물가가 전월보다 0.3%p 상승했다.",
        article_date="2025-11-04",
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
        snapshot=_snapshot([_record(value="0.3", unit="%")]),
    )

    assert result.status == "not_comparable"
    assert "값 성격" in result.reason or "단위" in result.reason
    assert any(not gate["passed"] for gate in result.gate_results)

def test_accepts_kosis_compact_month_period_in_snapshot():
    result = compare_claim_to_snapshot(
        claim_sentence="지난달 소비자 물가가 지난해 같은 달 대비 2.4% 상승했다.",
        article_date="2025-11-04",
        evidence_indicator="전년동월비(%)",
        evidence_selection={"지수종류": "총지수"},
        snapshot=_snapshot([_record(period="202510")]),
    )

    assert result.status == "match"
    assert result.official_period == "2025-10"
