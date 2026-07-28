from clafact.kosis_evidence_autofill import autofill_readiness_error


def test_autofill_requires_table_id_and_source_url_before_api_call():
    assert autofill_readiness_error("", "") == "KOSIS 통계표 ID를 먼저 입력해 주세요."
    assert autofill_readiness_error("DT_1B040A3", "") == "원본 URL을 먼저 입력해 주세요."
    assert autofill_readiness_error(
        "DT_1B040A3",
        "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B040A3",
    ) is None
