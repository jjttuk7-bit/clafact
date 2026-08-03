from clafact.kosis import KosisConnectionError
from clafact.kosis_catalog import crawl_catalog


class InterruptedCatalogClient:
    def fetch_statistics_list(self, _view_code, parent_id):
        if parent_id == "0":
            return [{"LIST_ID": "first"}, {"LIST_ID": "second"}]
        if parent_id == "first":
            return [{"TBL_ID": "T1", "TBL_NM": "저장해야 할 표"}]
        raise KosisConnectionError("temporary network failure")


def test_crawl_catalog_returns_partial_results_and_resume_queue_after_connection_error():
    result = crawl_catalog(InterruptedCatalogClient(), "MT_ZTITLE", ["0"], max_list_calls=3)

    assert result["tables"] == [{"TBL_ID": "T1", "TBL_NM": "저장해야 할 표"}]
    assert result["pending_parent_ids"] == ["second"]
    assert result["connection_error"] == "temporary network failure"
