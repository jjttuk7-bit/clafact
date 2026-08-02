from clafact.claim_completion import complete_claim_case


def _row(*, period="2024", value="230028"):
    return {
        "C1_OBJ_NM": "지역",
        "C1_NM": "전국",
        "ITM_NM": "출생아수",
        "UNIT_NM": "명",
        "PRD_DE": period,
        "DT": value,
        "LST_CHN_DE": "2025-02-26",
    }


def test_completes_a_claim_with_evidence_snapshot_and_match_verdict():
    completed = complete_claim_case(
        claim_id="CLM-001",
        sentence="2024년 전국 출생아 수는 230,028명이었다.",
        article_date="2025-02-27",
        org_id="101",
        table_id="DT_1B8000F",
        query_params={"prd_de": "2024"},
        rows=[_row()],
        evidence_indicator="출생아수",
        evidence_selection={"지역": "전국"},
        source_url="https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B8000F",
        retrieved_at="2026-08-02T16:00:00+09:00",
    )

    assert completed.verdict == "match"
    assert completed.snapshot_id.startswith("kosis-")
    assert completed.as_dict()["evidence"]["table_id"] == "DT_1B8000F"
    assert completed.as_dict()["comparison"]["status"] == "match"


def test_marks_a_missing_period_as_hold_in_the_completed_claim_record():
    completed = complete_claim_case(
        claim_id="CLM-003",
        sentence="2025년 전국 출생아 수는 230,028명이었다.",
        article_date="2026-02-27",
        org_id="101",
        table_id="DT_1B8000F",
        query_params={"prd_de": "2024"},
        rows=[_row()],
        evidence_indicator="출생아수",
        evidence_selection={"지역": "전국"},
        source_url="https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B8000F",
        retrieved_at="2026-08-02T16:00:00+09:00",
    )

    assert completed.verdict == "hold"
    assert completed.as_dict()["comparison"]["status"] == "not_comparable"
