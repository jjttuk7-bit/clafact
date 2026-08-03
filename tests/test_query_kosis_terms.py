import json

from clafact.assets.alias_dict import AliasDict
from clafact.pipeline.query_gen import make_query


def test_make_query_rewrites_news_phrases_to_kosis_indicator_terms(tmp_path):
    path = tmp_path / "aliases.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"alias": "소비자 물가 상승률", "canonical": "소비자물가지수 등락률"}, ensure_ascii=False),
            json.dumps({"alias": "건설업 취업자", "canonical": "산업별 취업자"}, ensure_ascii=False),
        ]),
        encoding="utf-8",
    )
    aliases = AliasDict(path)

    price_query = make_query("지난달 전체 소비자 물가 상승률(1.9%)보다 1.5%포인트 높다.", aliases)
    employment_query = make_query("지난달 건설업 취업자는 전년 동월 대비 16만9000명 감소했다.", aliases)

    assert "소비자물가지수" in price_query
    assert "등락률" in price_query
    assert "산업별 취업자" in employment_query
