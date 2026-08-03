import json

from clafact.kosis_catalog import CatalogIndex


def test_catalog_index_ranks_tables_using_title_survey_path_and_contents(tmp_path):
    snapshot = tmp_path / "catalog.json"
    snapshot.write_text(json.dumps({"tables": [
        {
            "TBL_ID": "CPI", "ORG_ID": "101", "TBL_NM": "소비자물가지수 등락률",
            "STAT_NM": "소비자물가조사", "MT_ATITLE": "물가 > 소비자물가",
            "CONTENTS": "품목별 소비자물가 상승률",
        },
        {
            "TBL_ID": "EMP", "ORG_ID": "101", "TBL_NM": "산업별 취업자",
            "STAT_NM": "경제활동인구조사", "MT_ATITLE": "고용 > 취업자",
            "CONTENTS": "산업별 취업자 수",
        },
    ]}, ensure_ascii=False), encoding="utf-8")

    index = CatalogIndex(snapshot)

    hits = index.search("소비자물가 상승률", top_k=2)

    assert [hit.tbl_id for hit in hits] == ["CPI"]
    assert hits[0].survey == "소비자물가조사"
