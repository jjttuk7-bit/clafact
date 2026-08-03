from urllib.parse import parse_qs, urlparse

from clafact.kosis import HttpKosisClient


def test_http_client_fetches_statistics_list_through_common_call_path(monkeypatch):
    client = HttpKosisClient(api_key="test-key")
    captured = {}

    def fake_call(url, note):
        captured["url"] = url
        captured["note"] = note
        return [{"TBL_ID": "T1", "TBL_NM": "표"}]

    monkeypatch.setattr(client, "_call", fake_call)

    assert client.fetch_statistics_list("MT_ZTITLE", "0") == [{"TBL_ID": "T1", "TBL_NM": "표"}]
    query = parse_qs(urlparse(captured["url"]).query)
    assert query["method"] == ["getList"]
    assert query["vwCd"] == ["MT_ZTITLE"]
    assert query["parentListId"] == ["0"]
