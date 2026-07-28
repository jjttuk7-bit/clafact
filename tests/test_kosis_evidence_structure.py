from clafact.kosis_evidence_input import build_manual_evidence


def test_manual_evidence_preserves_table_structure_type():
    evidence = build_manual_evidence(
        table_id="DT_1B040A3", url="https://kosis.kr/table", title="주민등록인구",
        organization="통계청", indicator="총인구", dimensions="시도",
        time_dimension="연", unit="명", definition="", source_selection="시도=전국",
        retrieved_at="2026-07-28T00:00:00+09:00", structure_type="time_series",
    )

    assert evidence.as_dict()["structure_type"] == "time_series"
