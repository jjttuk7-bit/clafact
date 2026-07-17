"""감사 추적(재현 버튼) 테스트 — 문서 20 기능 3.

가장 중요한 검사는 정확도가 아니라 **인증키가 새지 않는가**다.
데모는 공개 배포(Streamlit Cloud)이므로 URL 이 화면에 찍히는 순간 키가 유출된다.
"""
from pathlib import Path

from clafact import audit
from clafact.kosis import build_url, build_query, KEY_PLACEHOLDER, FixtureKosisClient
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.run import verify_sentence

ROOT = Path(__file__).resolve().parents[1]


def _engine():
    return (StatIndex(ROOT / "data/samples/kosis/tables_meta.json"),
            FixtureKosisClient(ROOT / "data/samples/kosis"))


# ── 인증키 유출 방지 ────────────────────────────────────────
def test_url_masks_key_by_default():
    url = build_url("101", "DT_1EA1019", prd_de="2024")
    assert KEY_PLACEHOLDER in url or "%7BKOSIS_API_KEY%7D" in url
    assert "apiKey=" in url


def test_audit_url_never_contains_real_key():
    """감사 추적의 URL 에 실 키가 들어가면 안 된다 — 회귀 시 즉시 실패해야 한다."""
    t = audit.build("FixtureKosisClient", "101", "DT_1EA1019", "표",
                    {"prd_de": "2024"}, [], [])
    assert "SECRETKEY" not in t.url
    assert KEY_PLACEHOLDER in t.url or "%7B" in t.url


def test_real_key_only_used_when_explicitly_passed():
    url = build_url("101", "T1", "REALKEY123", prd_de="2024")
    assert "REALKEY123" in url  # 실 호출 경로에서는 당연히 들어간다
    assert KEY_PLACEHOLDER not in url


# ── 실 호출과 재현 URL 이 같은 코드 경로인가 ──────────────────
def test_build_query_matches_verified_format():
    """2026-07-14 실 API 검증 형식 — objL1~8 전부 + newEstPrdCnt (누락 시 err 21)."""
    q = build_query("101", "DT_1EA1019", prd_de="2024")
    for i in range(1, 9):
        assert f"objL{i}" in q, f"objL{i} 누락 — err 21 발생 형식"
    assert q["newEstPrdCnt"], "newEstPrdCnt 누락 — err 21 발생 형식"
    assert q["orgId"] == "101" and q["tblId"] == "DT_1EA1019"


# ── 판정에 감사 추적이 붙는가 ────────────────────────────────
def test_verdict_carries_audit_trail():
    idx, client = _engine()
    r = verify_sentence("2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.",
                        "2025-05-14", idx, client)
    a = r.audit
    assert a, "판정에 감사 추적이 없다 — 재현 불가"
    assert a["org_id"] and a["tbl_id"], "orgId/tblId 가 없으면 재현 불가"
    assert a["params"]["prd_de"] == "2024"
    assert a["engine"] == "FixtureKosisClient", "어느 엔진으로 판정했는지 숨기지 않는다"
    assert a["rows"], "판정에 쓰인 행이 남아야 한다"
    assert a["url"].startswith("https://kosis.kr/openapi/")
    assert a["code_version"], "코드 버전 없으면 재현의 전제가 무너진다"


def test_audit_records_applied_rules():
    """파생 계산 판정은 A2-0007(연령비율)이 적용됐음을 남겨야 한다."""
    idx, client = _engine()
    r = verify_sentence("2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.",
                        "2025-05-14", idx, client)
    assert "A2-0007" in r.audit["rules"], f"적용 규칙 누락: {r.audit['rules']}"


def test_fixture_mode_is_disclosed():
    """픽스처로 판정했으면 그렇다고 적어야 한다 — 실시간인 척하지 않는다."""
    idx, client = _engine()
    r = verify_sentence("2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.",
                        "2025-05-14", idx, client)
    assert "픽스처" in r.audit["note"]


def test_not_claim_has_no_audit():
    idx, client = _engine()
    r = verify_sentence("경제 상황이 크게 악화되었다.", "2025-03-14", idx, client)
    assert r.label == "not_claim" and not r.audit


# ── 재현성: 같은 입력 → 같은 판정 ────────────────────────────
def test_verdict_is_deterministic():
    """결정적 로직이므로 재실행하면 반드시 같아야 한다 — 재현 버튼의 근거."""
    idx, client = _engine()
    s, d = "2024년 국내 과수 농가의 65세 이상 비율은 64.2%로 나타났다.", "2025-05-14"
    a = verify_sentence(s, d, idx, client)
    b = verify_sentence(s, d, idx, client)
    assert (a.label, a.calculation, a.evidence) == (b.label, b.calculation, b.evidence)
    assert a.audit["url"] == b.audit["url"]


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
