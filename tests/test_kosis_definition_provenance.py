from clafact.kosis_evidence_input import build_manual_evidence


def test_evidence_preserves_definition_source_and_approval_time():
    evidence = build_manual_evidence(
        table_id="DT_1B040A3", url="https://kosis.kr/table", title="주민등록인구",
        organization="통계청", indicator="총인구", dimensions="시도",
        time_dimension="연", unit="명", definition="주민등록표에 등재된 인구",
        source_selection="시도=전국", retrieved_at="2026-07-28T10:00:00+09:00",
        definition_provenance={
            "source_url": "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B040A3",
            "method": "meta_description",
            "approved_at": "2026-07-28T10:01:00+09:00",
        },
    )

    assert evidence.as_dict()["definition_provenance"]["method"] == "meta_description"
    assert evidence.as_dict()["definition_provenance"]["approved_at"] == "2026-07-28T10:01:00+09:00"
