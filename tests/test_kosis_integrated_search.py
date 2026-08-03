import pytest

from clafact.kosis import HttpKosisClient, KosisApiError


def test_integrated_search_treats_kosis_no_result_as_empty_candidates(monkeypatch):
    client = HttpKosisClient(api_key="test-key")

    def no_result(*_args, **_kwargs):
        raise KosisApiError({"err": "30", "errMsg": "데이터가 존재하지 않습니다."})

    monkeypatch.setattr(client, "_call", no_result)

    assert client.integrated_search("없는 검색어", resultCount=5) == []
