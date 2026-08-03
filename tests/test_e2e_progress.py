from clafact.eval.e2e_progress import build_e2e_progress


def test_separates_verified_snapshot_catalog_and_unmapped_cases():
    result = build_e2e_progress(
        [
            {"candidate_id": "verified", "gold_table_ids": ["T1"]},
            {"candidate_id": "coordinate_needed", "gold_table_ids": ["T1"]},
            {"candidate_id": "catalog_needed", "gold_table_ids": ["T2"]},
            {"candidate_id": "unmapped", "gold_table_ids": []},
        ],
        catalog_table_ids={"T1"},
        comparison_candidate_ids={"verified"},
    )

    assert result["summary"] == {
        "total": 4,
        "verdict_verified": 1,
        "needs_coordinates_and_snapshot": 1,
        "needs_catalog": 1,
        "no_table_mapping": 1,
    }
    assert result["cases"][2]["status"] == "needs_catalog"


def test_counts_final_unverifiable_case_without_table_as_verified():
    result = build_e2e_progress(
        [{"candidate_id": "unverifiable", "gold_table_ids": []}],
        catalog_table_ids=set(), comparison_candidate_ids={"unverifiable"},
    )
    assert result["summary"]["verdict_verified"] == 1
