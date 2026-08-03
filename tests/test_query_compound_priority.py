from clafact.assets.alias_dict import AliasDict
from clafact.pipeline.query_gen import make_query


def test_make_query_uses_numeric_household_compound_as_the_search_query(tmp_path):
    aliases = AliasDict(tmp_path / "missing.jsonl")

    query = make_query("1인 가구는 800만 가구를 돌파했다.", aliases)

    assert query == "1인가구"
