from pathlib import Path

from clafact.assets.alias_dict import AliasDict
from clafact.pipeline.query_gen import make_query


def test_default_aliases_cover_verified_kosis_search_terms():
    aliases = AliasDict(Path(__file__).resolve().parents[1] / "data/assets/aliases.jsonl")

    price_query = make_query("지난달 전체 소비자 물가 상승률(1.9%)보다 1.5%포인트 높다.", aliases)
    employment_query = make_query("지난달 건설업 취업자는 전년 동월 대비 16만9000명 감소했다.", aliases)

    assert "소비자물가지수" in price_query
    assert "산업별 취업자" in employment_query
