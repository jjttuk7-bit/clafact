import json

from clafact.kosis_catalog import crawl_catalog, save_catalog_snapshot


class CyclicCatalogClient:
    def fetch_statistics_list(self, _view_code, parent_id):
        return {
            "0": [{"LIST_ID": "A"}],
            "A": [{"LIST_ID": "0"}, {"TBL_ID": "T1", "TBL_NM": "표"}],
        }[parent_id]


def test_catalog_snapshot_persists_seen_nodes_and_blocks_cycles_on_resume(tmp_path):
    client = CyclicCatalogClient()
    first = crawl_catalog(client, "MT_ZTITLE", ["0"], max_list_calls=1)
    path = tmp_path / "catalog.json"
    save_catalog_snapshot(path, "MT_ZTITLE", first)
    saved = json.loads(path.read_text(encoding="utf-8"))

    second = crawl_catalog(client, "MT_ZTITLE", saved["pending_parent_ids"], max_list_calls=1,
                           seen_parent_ids=saved["seen_parent_ids"])

    assert second["tables"] == [{"TBL_ID": "T1", "TBL_NM": "표"}]
    assert second["pending_parent_ids"] == []
