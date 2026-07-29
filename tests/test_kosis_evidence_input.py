from clafact.kosis_evidence_input import build_candidate_evidence_prefill, build_manual_evidence


def test_manual_input_builds_traceable_kosis_evidence():
    evidence = build_manual_evidence(
        table_id="DT_1B040A3", url="https://kosis.kr/table", title="주민등록인구",
        organization="통계청", indicator="주민등록인구", dimensions="시도, 성별",
        time_dimension="연", unit="명", definition="주민등록 기준",
        source_selection="시도=전국;성별=계", retrieved_at="2026-07-28T18:30:00+09:00",
    )

    assert evidence.dimensions == ("시도", "성별")
    assert evidence.source_selection == {"시도": "전국", "성별": "계"}


def test_candidate_prefill_keeps_the_official_table_title_for_required_evidence_input():
    prefill = build_candidate_evidence_prefill(
        table_id="DT_1J22042",
        org_id="101",
        title="월별 소비자물가 등락률",
        indicator="전년동월비(%)",
    )

    assert prefill["table_id"] == "DT_1J22042"
    assert prefill["title"] == "월별 소비자물가 등락률"
    assert prefill["url"] == "https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1J22042"
