from clafact.claim_completion import complete_selected_claim


def test_completes_selected_persisted_evidence_without_refetching_kosis():
    snapshot = {
        "snapshot_id": "kosis-1",
        "reproducible_url": "https://kosis.kr/repro",
        "records": [{"PRD_DE": "2024", "DT": "230028"}],
    }
    completed = complete_selected_claim(
        shadow_run_id="shadow-1",
        row_index=1,
        sentence="2024년 전국 출생아 수는 230,028명이다.",
        mapping={"evidence_id": "DT_1B8000F:births", "table_id": "DT_1B8000F"},
        comparison={"status": "match", "claim_value": "230,028", "official_value": "230,028"},
        snapshot=snapshot,
    )

    assert completed["verdict"] == "match"
    assert completed["evidence_id"] == "DT_1B8000F:births"
    assert completed["snapshot"] == snapshot
    assert completed["evidence"]["source_url"] == "https://kosis.kr/repro"


def test_turns_non_comparable_selected_evidence_into_hold():
    completed = complete_selected_claim(
        shadow_run_id="shadow-1",
        row_index=1,
        sentence="2025년 전국 출생아 수는 230,028명이다.",
        mapping={"evidence_id": "DT_1B8000F:births", "table_id": "DT_1B8000F"},
        comparison={"status": "not_comparable", "reason": "기간 없음"},
        snapshot={"snapshot_id": "kosis-1", "reproducible_url": "https://kosis.kr/repro"},
    )

    assert completed["verdict"] == "hold"
