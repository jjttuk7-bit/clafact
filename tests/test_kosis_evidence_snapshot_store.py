from clafact.kosis_evidence_snapshot import build_evidence_snapshot
from clafact.kosis_evidence_snapshot_store import KosisEvidenceSnapshotStore


def test_snapshot_store_keeps_research_snapshot(tmp_path):
    snapshot = build_evidence_snapshot(
        org_id="101", table_id="DT_1B040A3", query_params={},
        retrieved_at="2026-07-28T10:00:00+09:00",
        rows=[{"PRD_DE": "2025", "DT": "50000000", "UNIT_NM": "명"}],
    )
    with KosisEvidenceSnapshotStore(tmp_path / "snapshots.db") as store:
        assert store.append(snapshot) is True
        assert store.get(snapshot.snapshot_id)["records"][0]["period"] == "2025"
