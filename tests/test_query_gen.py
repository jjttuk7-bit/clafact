"""Step 1 질의 생성 테스트 — 주장 문장 → 통계표 검색어.

핵심: 검색어에서 숫자·날짜·서술어는 빠지고, 통계 도메인어(지표·모집단)는 남아야 한다.
경로 C(통합검색)가 문장째가 아니라 이 검색어를 받는다.
"""
from pathlib import Path

from clafact.assets.alias_dict import AliasDict
from clafact.pipeline.query_gen import make_query, make_query_variants

ROOT = Path(__file__).resolve().parents[1]


def _empty():
    return AliasDict(ROOT / "data/assets/_none_qg.jsonl")  # 파일 없음 → 빈 사전


def _real():
    return AliasDict(ROOT / "data/assets/aliases.jsonl")


# ── 노이즈 제거 ─────────────────────────────────────────────
def test_removes_numbers_and_dates():
    q = make_query("2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.", _empty())
    assert "2024" not in q and "64.2" not in q and "65" not in q
    assert "년" not in q.split()  # '2024년' 통째로 제거


def test_removes_units_and_predicates():
    q = make_query("지난해 실업률은 7.2%로 나타났다.", _empty())
    assert "%" not in q
    assert "나타났다" not in q
    assert "지난해" not in q.split()  # 시점 상대어 제거


def test_keeps_domain_nouns():
    q = make_query("2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.", _empty())
    # 조사 벗긴 통계어가 남아야 한다
    assert "과수" in q
    assert "농가" in q
    assert "비율" in q


def test_strips_josa():
    q = make_query("서울의 1인 가구는 150만 가구를 넘어섰다.", _empty())
    assert "서울" in q          # '서울의' → '서울'
    assert "넘어" not in q       # 서술어 제거


def test_unit_noun_survives_when_subject():
    """'가구'는 단위이자 주제어 — '150만 가구'(수량)는 지우되 주제 '가구'는 살려야 한다.

    이 버그로 '서울의 1인 가구...' 검색어가 '서울' 하나로 뭉개졌었다.
    """
    q = make_query("서울의 1인 가구는 150만 가구를 넘어섰다.", _empty())
    assert "가구" in q, f"주제어 '가구'가 사라짐: {q}"


# ── 별칭 치환 (가장 큰 레버) ──────────────────────────────────
def test_alias_substitution_applied():
    q = make_query("일자리를 구하지 못한 사람의 비중이 늘었다.", _real())
    # aliases.jsonl 에 '일자리를 구하지 못한' → 실업률 계열 별칭이 있으면 통계어로 치환됨
    assert "실업" in q or "경제활동" in q, f"별칭 치환 안 됨: {q}"


# ── 폴백·변형 ──────────────────────────────────────────────
def test_empty_result_falls_back_to_sentence():
    # 통계어가 하나도 없는 문장이면 원문 폴백 (빈 검색어보다 낫다)
    q = make_query("2024년 3월 15%", _empty())
    assert q.strip() != ""


def test_variants_dedupe():
    v = make_query_variants("2024년 과수 농가 65세 이상 비율은 64.2%다.", _empty())
    assert len(v) == len(set(v)) and all(v)


def test_query_shorter_than_sentence():
    """검색어는 문장보다 짧아야 한다 — 통합검색 RANK 를 흐리지 않게."""
    s = "농가 고령화가 이어지면서 2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다."
    q = make_query(s, _empty())
    assert len(q) < len(s)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
