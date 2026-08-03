from clafact.kosis_catalog import crawl_catalog


class FakeCatalogClient:
    def __init__(self):
        self.calls = []

    def fetch_statistics_list(self, view_code, parent_id):
        self.calls.append((view_code, parent_id))
        return {
            "0": [
                {"LIST_ID": "topic", "LIST_NM": "주제"},
                {"TBL_ID": "ROOT_TABLE", "TBL_NM": "루트 표", "ORG_ID": "101"},
            ],
            "topic": [
                {"TBL_ID": "CHILD_TABLE", "TBL_NM": "하위 표", "ORG_ID": "101"},
            ],
        }.get(parent_id, [])


def test_crawl_catalog_collects_tables_and_keeps_unvisited_parents_for_resume():
    client = FakeCatalogClient()

    first = crawl_catalog(client, "MT_ZTITLE", ["0"], max_list_calls=1)

    assert first["tables"] == [{"TBL_ID": "ROOT_TABLE", "TBL_NM": "루트 표", "ORG_ID": "101"}]
    assert first["pending_parent_ids"] == ["topic"]
    assert first["visited_parent_ids"] == ["0"]

    second = crawl_catalog(client, "MT_ZTITLE", first["pending_parent_ids"], max_list_calls=1)

    assert second["tables"] == [{"TBL_ID": "CHILD_TABLE", "TBL_NM": "하위 표", "ORG_ID": "101"}]
    assert second["pending_parent_ids"] == []
