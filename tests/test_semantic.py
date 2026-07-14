"""경로 B(의미 검색) + 하이브리드 + EXP-001 회귀 테스트."""
import json
from pathlib import Path

from clafact.assets.alias_dict import AliasDict
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.retrieve_semantic import (
    SemanticIndex, CharNgramEmbedder, char_ngrams, cosine,
)

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/samples/kosis/tables_meta.json"
TABLES = json.loads(META.read_text(encoding="utf-8"))


def test_empty_alias_injection_respected():
    """규칙 A2-0010: 명시적 빈 사전 주입이 기본 사전으로 폴백되면 안 된다."""
    empty = AliasDict(ROOT / "data/assets/_none_test.jsonl")
    idx = StatIndex(META, aliases=empty)
    assert len(idx.aliases) == 0, "빈 사전을 줬는데 기본 사전이 로드됨 (falsy 폴백 버그)"


def test_semantic_beats_keyword_on_form_similarity():
    """경로 B: '농사짓는 고령 인구' → 농가 통계 (문자 유사 '농사'~'농가').
    키워드 자카드로는 놓치는 케이스를 의미 검색이 잡는다."""
    sem = SemanticIndex(TABLES)
    hits = [t for t, _ in sem.search("농사짓는 고령 인구가 증가했다")]
    assert "DT_1EA1019" in hits[:3]


def test_alias_catches_synonym_trap():
    """A1 별칭: '일자리를 구하지 못한' → 실업률 (동의어 함정, 의미 검색도 놓침)."""
    alias = AliasDict(ROOT / "data/assets/aliases.jsonl")
    idx = StatIndex(META, aliases=alias)
    hits = [h.tbl_id for h in idx.search("일자리를 구하지 못한 사람의 비중이 늘었다")]
    assert hits[0] == "DT_1DA7002"


def test_char_ngram_basics():
    grams = char_ngrams("실업률")
    assert "실업률" in grams and "실업" in grams
    a = CharNgramEmbedder().fit(["실업률 고용", "출생아 인구"])
    v = a.embed(["실업률"])[0]
    assert v and cosine(v, v) == 1.0


def test_hybrid_reaches_full_coverage():
    """EXP-001 회귀: 하이브리드(별칭+의미)가 매핑 평가셋 Hit@3=1.0 을 유지."""
    eval_path = ROOT / "data/goldenset/mapping_eval.jsonl"
    cases = [json.loads(l) for l in eval_path.read_text(encoding="utf-8").strip().splitlines()]
    alias = AliasDict(ROOT / "data/assets/aliases.jsonl")
    idx_al = StatIndex(META, aliases=alias)
    sem = SemanticIndex(TABLES, aliases=alias)

    def rrf(lists, k=60, top=3):
        score = {}
        for rl in lists:
            for rank, tid in enumerate(rl):
                score[tid] = score.get(tid, 0.0) + 1.0 / (k + rank + 1)
        return [t for t, _ in sorted(score.items(), key=lambda x: -x[1])][:top]

    hit3 = 0
    for c in cases:
        a = [h.tbl_id for h in idx_al.search(c["query"], 5)]
        b = [t for t, _ in sem.search(c["query"], 5)]
        top = rrf([a, b])
        hit3 += c["gold_tbl_id"] in top
    assert hit3 == len(cases), f"하이브리드 Hit@3 저하: {hit3}/{len(cases)}"


if __name__ == "__main__":
    import sys, traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS  {fn.__name__}")
        except Exception:
            failed += 1; print(f"  FAIL  {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
