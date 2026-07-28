from clafact.kosis_snapshot_compare import compare_snapshots


def test_compare_snapshots_detects_value_and_revision_change():
    before = {
        "snapshot_id": "before",
        "records": [{
            "period": "2025", "indicator": "총인구", "selection": {"시도": "전국"},
            "value": "50000000", "last_changed_at": "2026-06-01",
        }],
    }
    after = {
        "snapshot_id": "after",
        "records": [{
            "period": "2025", "indicator": "총인구", "selection": {"시도": "전국"},
            "value": "50001000", "last_changed_at": "2026-06-30",
        }],
    }

    result = compare_snapshots(before, after)

    assert result.changed_count == 1
    assert result.rows[0]["change_type"] == "changed"
    assert result.rows[0]["value_before"] == "50000000"
    assert result.rows[0]["value_after"] == "50001000"


def test_compare_snapshots_detects_new_record():
    result = compare_snapshots(
        {"snapshot_id": "before", "records": []},
        {"snapshot_id": "after", "records": [{
            "period": "2025", "indicator": "총인구", "selection": {},
            "value": "50000000", "last_changed_at": "",
        }]},
    )

    assert result.added_count == 1
    assert result.rows[0]["change_type"] == "added"
