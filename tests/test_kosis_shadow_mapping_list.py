from clafact.kosis_shadow_mapping import KosisShadowMapping
from clafact.kosis_shadow_mapping_store import KosisShadowMappingStore


def test_mapping_store_lists_mappings_for_table(tmp_path):
    mapping = KosisShadowMapping(
        shadow_run_id="shadow-001", row_index=3, table_id="DT_1B040A3",
        source_selection={"시도": "전국"}, note="", status="candidate",
    )
    with KosisShadowMappingStore(tmp_path / "mapping.db") as store:
        store.append(mapping)
        assert store.list_for_table("DT_1B040A3")[0]["shadow_run_id"] == "shadow-001"
