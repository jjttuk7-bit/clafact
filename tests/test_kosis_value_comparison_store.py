from clafact.kosis_value_comparison import KosisValueComparison
from clafact.kosis_value_comparison_store import KosisValueComparisonStore


def _comparison():
    return KosisValueComparison(
        status="match",
        reason="값 일치",
        claim_value="2.4%",
        official_value="2.4%",
        claim_period="2025-10",
        official_period="2025-10",
        snapshot_id="kosis-snapshot-1",
        snapshot_retrieved_at="2026-07-29T10:00:00+09:00",
        tolerance=0.05,
    )


def test_value_comparison_store_preserves_research_result_by_evidence_and_snapshot(tmp_path):
    with KosisValueComparisonStore(tmp_path / "comparison.db") as store:
        assert store.append(
            shadow_run_id="shadow-001",
            row_index=1,
            evidence_id="DT_1J22042:year",
            comparison=_comparison(),
        ) is True
        saved = store.list_for_run("shadow-001")

    assert saved[0]["status"] == "match"
    assert saved[0]["snapshot_id"] == "kosis-snapshot-1"


def test_value_comparison_store_rejects_changed_payload_for_same_reproducible_key(tmp_path):
    with KosisValueComparisonStore(tmp_path / "comparison.db") as store:
        store.append(
            shadow_run_id="shadow-001",
            row_index=1,
            evidence_id="DT_1J22042:year",
            comparison=_comparison(),
        )
        changed = _comparison().__class__(
            **{**_comparison().as_dict(), "status": "mismatch"}
        )

        try:
            store.append(
                shadow_run_id="shadow-001",
                row_index=1,
                evidence_id="DT_1J22042:year",
                comparison=changed,
            )
        except ValueError as error:
            assert "different payload" in str(error)
        else:
            raise AssertionError("different comparison payload must not overwrite research history")
