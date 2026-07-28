import json
import sqlite3

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


def test_store_preserves_multiple_indicators_from_one_kosis_table(tmp_path):
    common = dict(
        table_id="DT_1J22042", url="https://kosis.kr/table", title="월별 소비자물가 등락률",
        organization="통계청", dimensions=("지수종류",), time_dimension="월", unit="%",
        definition="", source_selection={"지수종류": "총지수"},
        retrieved_at="2026-07-29T07:00:00+09:00",
    )
    month_over_month = KosisEvidenceObject(indicator="전월비(%)", **common)
    year_over_year = KosisEvidenceObject(indicator="전년동월비(%)", **common)

    with KosisEvidenceStore(tmp_path / "kosis_evidence.db") as store:
        assert store.append(month_over_month) is True
        assert store.append(year_over_year) is True
        saved = store.list_all()

    assert {item["indicator"] for item in saved} == {"전월비(%)", "전년동월비(%)"}
    assert {item["evidence_id"] for item in saved} == {
        month_over_month.evidence_id, year_over_year.evidence_id
    }

def test_store_migrates_legacy_table_id_rows_without_losing_them(tmp_path):
    database_path = tmp_path / "kosis_evidence.db"
    legacy_payload = _evidence().as_dict()
    legacy_payload.pop("evidence_id")
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            "CREATE TABLE kosis_evidence (table_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO kosis_evidence VALUES (?, ?)",
            ("DT_1B040A3", json.dumps(legacy_payload, ensure_ascii=False, sort_keys=True)),
        )

    with KosisEvidenceStore(database_path) as store:
        saved = store.list_all()

    assert saved[0]["table_id"] == "DT_1B040A3"
    assert saved[0]["evidence_id"] == _evidence().evidence_id
