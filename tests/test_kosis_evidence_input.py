from clafact.kosis_evidence_input import build_manual_evidence


def test_manual_input_builds_traceable_kosis_evidence():
    evidence = build_manual_evidence(
        table_id="DT_1B040A3", url="https://kosis.kr/table", title="주민등록인구",
        organization="통계청", indicator="주민등록인구", dimensions="시도, 성별",
        time_dimension="연", unit="명", definition="주민등록 기준",
        source_selection="시도=전국;성별=계", retrieved_at="2026-07-28T18:30:00+09:00",
    )

    assert evidence.dimensions == ("시도", "성별")
    assert evidence.source_selection == {"시도": "전국", "성별": "계"}
