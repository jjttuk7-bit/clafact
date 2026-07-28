from clafact.kosis_evidence_snapshot import build_evidence_snapshot
from clafact.kosis_evidence_snapshot_store import KosisEvidenceSnapshotStore


def test_snapshot_store_lists_table_history_newest_first(tmp_path):
    first = build_evidence_snapshot(
        org_id="101", table_id="DT_1B040A3", query_params={},
        retrieved_at="2026-07-27T10:00:00+09:00",
        rows=[{"PRD_DE": "2025", "DT": "50000000"}],
    )
    second = build_evidence_snapshot(
        org_id="101", table_id="DT_1B040A3", query_params={},
        retrieved_at="2026-07-28T10:00:00+09:00",
        rows=[{"PRD_DE": "2025", "DT": "50001000"}],
    )
    with KosisEvidenceSnapshotStore(tmp_path / "snapshots.db") as store:
        store.append(first)
        store.append(second)
        assert [item["snapshot_id"] for item in store.list_for_table("DT_1B040A3")] == [
            second.snapshot_id, first.snapshot_id
        ]
