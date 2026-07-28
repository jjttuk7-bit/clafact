from clafact.kosis_evidence import KosisEvidenceObject
from clafact.kosis_evidence_store import KosisEvidenceStore


def test_evidence_store_lists_saved_objects(tmp_path):
    evidence = KosisEvidenceObject(
        table_id="DT_1B040A3", url="https://kosis.kr/table", title="주민등록인구",
        organization="통계청", indicator="주민등록인구", dimensions=("시도",),
        time_dimension="연", unit="명", definition="등록 인구", source_selection={"시도": "전국"},
        retrieved_at="2026-07-28T00:00:00+09:00",
    )
    with KosisEvidenceStore(tmp_path / "evidence.db") as store:
        store.append(evidence)
        assert store.list_all()[0]["title"] == "주민등록인구"
