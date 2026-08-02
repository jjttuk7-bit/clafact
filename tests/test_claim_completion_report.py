from clafact.claim_completion_report import complete_claim_cases


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


def test_completes_match_mismatch_and_hold_cases_in_one_reproducible_report():
    common = {
        "article_date": "2025-02-27",
        "org_id": "101",
        "table_id": "DT_1B8000F",
        "query_params": {"prd_de": "2024"},
        "rows": [_row()],
        "evidence_indicator": "출생아수",
        "evidence_selection": {"지역": "전국"},
        "source_url": "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B8000F",
        "retrieved_at": "2026-08-02T16:00:00+09:00",
    }

    report = complete_claim_cases([
        {**common, "claim_id": "CLM-001", "sentence": "2024년 전국 출생아 수는 230,028명이었다."},
        {**common, "claim_id": "CLM-002", "sentence": "2024년 전국 출생아 수는 240,000명이었다."},
        {**common, "claim_id": "CLM-003", "sentence": "2025년 전국 출생아 수는 230,028명이었다."},
    ])

    assert [case["verdict"] for case in report] == ["match", "mismatch", "hold"]
    assert all(case["snapshot_id"].startswith("kosis-") for case in report)
