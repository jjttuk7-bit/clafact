from clafact.kosis_shadow_mapping import KosisShadowMapping
from clafact.kosis_shadow_mapping_store import KosisShadowMappingStore


def test_mapping_store_keeps_research_mapping(tmp_path):
    mapping = KosisShadowMapping(
        shadow_run_id="shadow-001",
        row_index=3,
        table_id="DT_1B040A3",
        source_selection={"시도": "전국"},
        note="인구 지표 후보 근거",
        status="candidate",
    )
    with KosisShadowMappingStore(tmp_path / "mapping.db") as store:
        assert store.append(mapping) is True
        assert store.list_for_run("shadow-001")[0]["table_id"] == "DT_1B040A3"