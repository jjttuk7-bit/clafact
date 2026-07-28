import pytest

from clafact.kosis_evidence import KosisEvidenceObject


def test_kosis_evidence_object_preserves_traceable_table_structure():
    evidence = KosisEvidenceObject(
        table_id="DT_1B040A3",
        url="https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1B040A3",
        title="주민등록인구",
        organization="통계청",
        indicator="주민등록인구",
        dimensions=("시도", "성별"),
        time_dimension="연",
        unit="명",
        definition="주민등록 기준 인구",
        source_selection={"시도": "전국", "성별": "계"},
        retrieved_at="2026-07-28T18:00:00+09:00",
    )

    assert evidence.as_dict()["dimensions"] == ["시도", "성별"]
    assert evidence.as_dict()["source_selection"]["성별"] == "계"


def test_kosis_evidence_object_requires_table_identity_and_provenance():
    with pytest.raises(ValueError, match="table_id"):
        KosisEvidenceObject(
            table_id="", url="", title="", organization="", indicator="",
            dimensions=(), time_dimension="", unit="", definition="",
            source_selection={}, retrieved_at="",
        )
