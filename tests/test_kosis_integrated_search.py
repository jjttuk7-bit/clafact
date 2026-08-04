import json

import pytest

from clafact.kosis import HttpKosisClient, KosisApiError, parse_json_tolerant


def test_integrated_search_treats_kosis_no_result_as_empty_candidates(monkeypatch):
    client = HttpKosisClient(api_key="test-key")

    def no_result(*_args, **_kwargs):
        raise KosisApiError({"err": "30", "errMsg": "데이터가 존재하지 않습니다."})

    monkeypatch.setattr(client, "_call", no_result)

    assert client.integrated_search("없는 검색어", resultCount=5) == []


def test_integrated_search_survives_unrecoverable_parse_failure(monkeypatch):
    """실측 발견(2026-08-04): '노년부양비' 검색이 실 KOSIS에서 깨진 JSON을 유발해
    JSONDecodeError로 배치 전체가 죽었다. 검색 실패는 판단불가로만 이어져야 한다."""
    client = HttpKosisClient(api_key="test-key")

    def broken(*_args, **_kwargs):
        raise json.JSONDecodeError("Expecting ',' delimiter", "{bad", 4)

    monkeypatch.setattr(client, "_call", broken)

    assert client.integrated_search("노년부양비", resultCount=5) == []


def test_parse_json_tolerant_does_not_mangle_latin_abbreviations_in_prose():
    """실측 발견(2026-08-04): 이전 정규식은 대소문자 섞인 임의 단어까지 키로 오인했다.
    통계 설명문 안의 'Pt:', 'T:'(수식 변수 설명) 때문에 '노년부양비' 검색 응답 전체가
    파싱 실패했던 실제 사례를 재현한다."""
    broken = (
        '[{ORG_ID:"101",TBL_NM:"주요 인구지표",'
        'ITEM03:"인구성장률= ln(Pt/P0)/T*100 '
        '(P0: 기준연도 인구, Pt: 비교연도 인구, T: 비교기간)"}]'
    )
    data = parse_json_tolerant(broken)
    assert data[0]["ORG_ID"] == "101"
    assert "Pt: 비교연도 인구" in data[0]["ITEM03"]
