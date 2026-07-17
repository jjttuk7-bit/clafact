"""경로 C — KOSIS 통합검색 매핑 테스트 (오프라인 픽스처).

실 API 없이 클라이언트·시점필터·파서·TableHit 배선을 검증한다.
클라우드에서 HttpKosisClient 로 스위치하면 같은 코드가 진짜 28만 표를 검색한다.
"""
import io
from pathlib import Path

from clafact.kosis import (FixtureKosisClient, HttpKosisClient, build_search_url,
                           parse_json_tolerant, KEY_PLACEHOLDER, SEARCH_URL)
from clafact.throttle import CallBudget, RateLimiter
from clafact.pipeline.retrieve_kosis import search_kosis, _covers_period
from clafact.pipeline.query_gen import make_query
from clafact.assets.alias_dict import AliasDict

ROOT = Path(__file__).resolve().parents[1]


def _fixture():
    return FixtureKosisClient(ROOT / "data/samples/kosis")


# ── 검색 URL·파서 ──────────────────────────────────────────
def test_search_url_masks_key():
    url = build_search_url("과수 농가")
    assert url.startswith(SEARCH_URL)
    assert KEY_PLACEHOLDER in url and "searchNm=" in url and "sort=RANK" in url


def test_tolerant_parser_handles_normal_json():
    assert parse_json_tolerant('[{"A":"1"}]') == [{"A": "1"}]


def test_tolerant_parser_fixes_unquoted_keys():
    """2026-07-15 통합검색에서 관찰된 '키 따옴표 없음' 형태 방어."""
    assert parse_json_tolerant('[{ORG_ID:"101",TBL_ID:"DT_X"}]') == \
        [{"ORG_ID": "101", "TBL_ID": "DT_X"}]


# ── 시점 필터 ──────────────────────────────────────────────
def test_period_filter_keeps_when_unknown():
    """수록기간 모르면 후보 유지 (못 재는 걸로 버리지 않음)."""
    assert _covers_period({"STRT_PRD_DE": "", "END_PRD_DE": ""}, "2024") is True


def test_period_filter_drops_out_of_range():
    row = {"STRT_PRD_DE": "2010", "END_PRD_DE": "2020"}
    assert _covers_period(row, "2024") is False
    assert _covers_period(row, "2015") is True


# ── 검색 (픽스처) ──────────────────────────────────────────
def test_search_returns_tablehits():
    hits = search_kosis("과수 농가 연령", _fixture())
    assert hits, "검색 결과 없음"
    assert all(h.tbl_id and h.org_id for h in hits)
    assert hits[0].score >= hits[-1].score  # RANK 순 점수

def test_search_finds_relevant_table():
    """'과수 농가 연령' → 농림어업조사 표(DT_1EA1019)가 후보에 있어야 한다."""
    hits = search_kosis("과수 농가 연령 영농형태", _fixture())
    assert "DT_1EA1019" in [h.tbl_id for h in hits]


def test_search_with_query_gen():
    """query_gen 검색어 → 경로 C 파이프라인 (실전 조합)."""
    al = AliasDict(ROOT / "data/assets/aliases.jsonl")
    q = make_query("2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.", al)
    hits = search_kosis(q, _fixture())
    assert "DT_1EA1019" in [h.tbl_id for h in hits]


# ── 예산 회귀 (통합검색도 예산을 쓴다) ───────────────────────
def test_http_search_spends_budget():
    import urllib.request
    d = Path(__import__("tempfile").mkdtemp())
    orig = urllib.request.urlopen
    try:
        b = CallBudget(d / "b.json", limit=10)
        c = HttpKosisClient(api_key="DUMMY", budget=b, rate_limiter=RateLimiter(600))

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        urllib.request.urlopen = lambda *a, **k: Resp(b'[{"TBL_ID":"DT_X","ORG_ID":"101","TBL_NM":"t"}]')
        rows = c.integrated_search("과수")
        assert len(rows) == 1 and b.used() == 1
    finally:
        urllib.request.urlopen = orig
        __import__("shutil").rmtree(d)


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
