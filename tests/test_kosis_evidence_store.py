from clafact.kosis_evidence import KosisEvidenceObject
from clafact.kosis_evidence_store import KosisEvidenceStore


def _evidence() -> KosisEvidenceObject:
    return KosisEvidenceObject(
        table_id="DT_1B040A3", url="https://kosis.kr/table", title="주민등록인구",
        organization="통계청", indicator="주민등록인구", dimensions=("시도",),
        time_dimension="연", unit="명", definition="주민등록 기준",
        source_selection={"시도": "전국"}, retrieved_at="2026-07-28T18:00:00+09:00",
    )


def test_store_appends_and_reads_traceable_evidence(tmp_path):
    with KosisEvidenceStore(tmp_path / "kosis_evidence.db") as store:
        assert store.append(_evidence()) is True
        saved = store.get("DT_1B040A3")

    assert saved["indicator"] == "주민등록인구"
    assert saved["source_selection"] == {"시도": "전국"}
