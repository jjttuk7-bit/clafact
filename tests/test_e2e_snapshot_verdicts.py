from clafact.eval.e2e_snapshot_verdicts import evaluate_change_rate_snapshots


def test_evaluates_two_snapshot_values_as_a_traceable_match():
    result = evaluate_change_rate_snapshots(
        candidate_id="NEWS_B-030",
        claimed=3.4,
        base_snapshot={"snapshot_id": "base", "records": [{"value": "106.09"}]},
        current_snapshot={"snapshot_id": "current", "records": [{"value": "109.67"}]},
        tolerance=0.05,
    )

    assert result["verdict"] == "match"
    assert result["official"] == 3.3744933546988376
    assert result["snapshot_ids"] == ["base", "current"]
