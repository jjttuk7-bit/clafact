from clafact.claim_completion import complete_claim_case


def test_completed_claim_keeps_the_full_immutable_snapshot_for_replay():
    completed = complete_claim_case(
        claim_id="CLM-001",
        sentence="2024년 전국 출생아 수는 230,028명이었다.",
        article_date="2025-02-27",
        org_id="101",
        table_id="DT_1B8000F",
        query_params={"prd_de": "2024"},
        rows=[{
            "C1_OBJ_NM": "지역", "C1_NM": "전국", "ITM_NM": "출생아수",
            "UNIT_NM": "명", "PRD_DE": "2024", "DT": "230028",
        }],
        evidence_indicator="출생아수",
        evidence_selection={"지역": "전국"},
        source_url="https://example.invalid/ignored",
        retrieved_at="2026-08-02T16:00:00+09:00",
    ).as_dict()

    snapshot = completed["snapshot"]
    assert snapshot["content_hash"]
    assert snapshot["query_params"] == {"prd_de": "2024"}
    assert snapshot["records"][0]["value"] == "230028"
    assert "orgId=101" in snapshot["reproducible_url"]
    assert completed["evidence"]["source_url"] == snapshot["reproducible_url"]
