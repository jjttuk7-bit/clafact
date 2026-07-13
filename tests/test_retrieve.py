"""KOSIS Retriever(경로 A 기준선) + 픽스처 풀체인 테스트.

⚠️ 픽스처 수치 중 DT_1EA1019 는 클라비 제시 사례의 실제 값, DT_1DA7002 는 개발용 가상 값.
"""
from pathlib import Path

from clafact.kosis import FixtureKosisClient
from clafact.pipeline.retrieve import StatIndex, fetch_evidence
from clafact.pipeline.parse import parse_claim
from clafact.pipeline.verdict import compare, derived_ratio
from clafact.schemas import VerdictLabel

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/samples/kosis/tables_meta.json"
FIXTURES = ROOT / "data/samples/kosis"


def _index() -> StatIndex:
    return StatIndex(META)


def test_search_fruit_farm():
    hits = _index().search("과수 농가 경영주 고령")
    assert hits and hits[0].tbl_id == "DT_1EA1019"


def test_search_unemployment():
    hits = _index().search("실업률")
    assert hits and hits[0].tbl_id == "DT_1DA7002"


def test_alias_substitution_helps():
    """A1 별칭 사전: '과일 재배'(기사어) → '영농형태 과수'(통계어) 치환으로 검색 적중"""
    idx = _index()  # aliases.jsonl 시드 로딩
    hits = idx.search("과일 재배 농가 고령화 비율")
    assert hits and hits[0].tbl_id == "DT_1EA1019"


def test_search_miss_returns_empty():
    """대응 통계 부재 → 빈 결과 → 상위에서 판단불가 분기 (억지 매핑 금지)"""
    assert _index().search("암호화폐 시세") == []


def test_fetch_evidence_filters():
    client = FixtureKosisClient(FIXTURES)
    hit = _index().search("과수 농가 경영주")[0]
    ev = fetch_evidence(client, hit, period="2024", c1="과수", c2="계")
    assert len(ev) == 1 and ev[0].value == 166558 and ev[0].unit == "가구"
    assert ev[0].query_params["prd_de"] == "2024"  # 재현 가능성 (FR-12)


def test_full_chain_kosis_case():
    """머니 테스트 — 키 없이 풀체인:
    기사 문장 → parse → 검색 → 픽스처 조회 → 파생 계산 재현 → 판정 MATCH.
    (클라비 제시 사례: 과수 농가 고령화 64.2%)"""
    sentence = "2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다."
    pc = parse_claim(sentence, "2025-03-14")
    assert pc.parse_complete and pc.period == "2024"
    claimed = pc.quantities[0]                      # 64.2 %

    idx, client = _index(), FixtureKosisClient(FIXTURES)
    hit = idx.search("과수 농가 경영주 연령 고령")[0]

    total = fetch_evidence(client, hit, pc.period, c1="과수", c2="계")[0]
    aged = [e for e in fetch_evidence(client, hit, pc.period, c1="과수")
            if e.query_params["c2"] in ("65~69세", "70~74세", "75~79세", "80세 이상")]
    assert len(aged) == 4

    ratio = derived_ratio([e.value for e in aged], total.value) * 100  # 64.168…
    res = compare(claimed.value, claimed.composed_unit, ratio, "%")
    assert res.verdict.label == VerdictLabel.MATCH
    assert res.verdict.confidence == "high"


def test_mock_llm_roundtrip():
    from clafact.llm import MockLLMClient
    mock = MockLLMClient()
    mock.on("주장 판별", lambda u: '{"verifiable": true}')
    assert mock.complete("주장 판별기", "실업률은 7.2%였다") == '{"verifiable": true}'
    assert mock.calls[0]["user"].startswith("실업률")


if __name__ == "__main__":
    import sys, traceback
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
    sys.exit(1 if failed else 0)
