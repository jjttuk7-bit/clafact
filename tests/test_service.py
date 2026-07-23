"""서비스 v0 테스트 — 멱등성·격리·등급 분류·리뷰 큐 (문서 25 S0 완료 기준)."""
import json
import tempfile
from pathlib import Path

from clafact.kosis import FixtureKosisClient
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.run import ClaimResult
from clafact.service import batch, store as st
from clafact.service.store import Store

ROOT = Path(__file__).resolve().parents[1]
IDX = StatIndex(ROOT / "data/samples/kosis/tables_meta.json")
CL = FixtureKosisClient(ROOT / "data/samples/kosis")

ARTICLES = [
    {"title": "실업률 급등", "date": "2025-06-20", "url": "http://x.test/1",
     "body": "올해 실업률이 10%에 달했다."},
    {"title": "1인 가구", "date": "2025-06-02", "url": "http://x.test/2",
     "body": "서울의 1인 가구는 150만 가구를 넘어섰다. 지난해 출생아 수는 23만 명으로 역대 최저를 기록했다."},
    {"title": "코인", "date": "2025-06-20", "url": "http://x.test/3",
     "body": "비트코인 가격이 1억 원을 넘어섰다."},
]


def _jsonl(rows) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                    encoding="utf-8")
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    f.close()
    return f.name


def _store() -> Store:
    return Store(":memory:")


def test_ingest_idempotent():
    """같은 파일을 두 번 넣어도 기사·Claim 이 늘지 않는다 (§4.2 원칙 1)."""
    s = _store()
    path = _jsonl(ARTICLES)
    first = batch.ingest_file(s, path)
    assert first["articles_new"] == 3 and first["claims_new"] >= 4
    second = batch.ingest_file(s, path)
    assert second["articles_new"] == 0 and second["claims_new"] == 0
    s.close()


def test_process_e2e_and_triage():
    """실 파이프라인으로 처리 → 불일치/저신뢰는 리뷰 큐, 판단불가는 그대로."""
    s = _store()
    batch.ingest_file(s, _jsonl(ARTICLES))
    stats = batch.process_pending(s, IDX, CL)
    assert stats["failed"] == 0 and stats["processed"] >= 4
    summary = s.summary()
    assert summary["claims_by_status"].get("PENDING") is None       # 큐 소진
    assert summary["claims_by_label"]["mismatch"] >= 1              # 실업률 10%
    assert summary["claims_by_label"]["unverifiable"] >= 1          # 비트코인 → 범위 밖
    # 불일치·match-low·match-medium 전부 사람 몫 (자동확정은 high+직접조회만)
    assert summary["claims_by_tier"]["NEEDS_REVIEW"] >= 3
    s.close()


def test_reprocess_is_noop():
    """처리 완료 후 다시 process 를 돌려도 재판정하지 않는다 (멱등성 2축)."""
    s = _store()
    batch.ingest_file(s, _jsonl(ARTICLES))
    batch.process_pending(s, IDX, CL)
    again = batch.process_pending(s, IDX, CL)
    assert again["processed"] == 0 and again["failed"] == 0
    s.close()


def test_process_pending_limits_work_to_selected_article_ids():
    """업로드 범위를 지정하면 기존 대기열은 처리하지 않는다."""
    s = _store()
    s.upsert_article("art_uploaded", "새 업로드", "2025-01-01", "", "u1", "b")
    s.upsert_article("art_existing", "기존 기사", "2025-01-01", "", "u2", "b")
    s.enqueue_claim("clm_uploaded", "art_uploaded", "새 기사 수치는 1%다.")
    s.enqueue_claim("clm_existing", "art_existing", "기존 기사 수치는 2%다.")

    def unverifiable(sentence, article_date):
        return ClaimResult(sentence=sentence, label="unverifiable", reason="테스트")

    stats = batch.process_pending(s, article_ids=["art_uploaded"], verify=unverifiable)

    assert stats["processed"] == 1
    statuses = {row["claim_id"]: row["status"] for row in s.conn.execute(
        "SELECT claim_id, status FROM claims").fetchall()}
    assert statuses == {"clm_uploaded": st.DONE, "clm_existing": st.PENDING}
    s.close()
def test_failure_isolation():
    """Claim 1건의 예외가 배치를 죽이지 않는다 (§4.2 원칙 2)."""
    s = _store()
    batch.ingest_file(s, _jsonl(ARTICLES))

    def bomb(sentence, article_date):
        if "실업률" in sentence:
            raise RuntimeError("의도된 폭탄")
        return ClaimResult(sentence=sentence, label="unverifiable",
                           reason="테스트 스텁")

    stats = batch.process_pending(s, verify=bomb)
    assert stats["failed"] == 1 and stats["processed"] >= 3
    failed = s.conn.execute(
        "SELECT * FROM claims WHERE status='FAILED'").fetchall()
    assert len(failed) == 1 and "의도된 폭탄" in failed[0]["error"]
    s.close()


def test_triage_rules():
    """등급 게이트 (문서 25 §5.1): 불일치는 무조건 리뷰, 자동확정은 high+무계산만."""
    mk = lambda **kw: ClaimResult(sentence="s", **kw)
    assert batch.triage(mk(label="mismatch", confidence="high")) == st.NEEDS_REVIEW
    assert batch.triage(mk(label="match", confidence="high")) == st.AUTO_CONFIRMED
    assert batch.triage(mk(label="match", confidence="high",
                           calculation="a/b")) == st.NEEDS_REVIEW  # 파생 계산 경유
    assert batch.triage(mk(label="match", confidence="low")) == st.NEEDS_REVIEW
    assert batch.triage(mk(label="unverifiable")) == st.UNVERIFIABLE
    assert batch.triage(mk(label="not_claim")) == st.SKIPPED


def test_review_queue_order_and_actions():
    """리뷰 큐는 불일치 → low → medium 순. approve/correct/reject 전이."""
    s = _store()
    s.upsert_article("art_t", "t", "2025-01-01", "", "u", "b")
    rows = [("clm_a", "match", "medium"), ("clm_b", "mismatch", "high"),
            ("clm_c", "match", "low")]
    for cid, label, conf in rows:
        s.enqueue_claim(cid, "art_t", f"문장 {cid}")
        s.save_result(cid, label=label, confidence=conf, tier=st.NEEDS_REVIEW)
    q = [r["claim_id"] for r in s.review_queue()]
    assert q == ["clm_b", "clm_c", "clm_a"]   # 불일치 → low → medium

    s.apply_review("clm_b", "approve")
    s.apply_review("clm_c", "correct", note="값 보정")
    s.apply_review("clm_a", "reject", note="재처리")
    tiers = {r["claim_id"]: (r["tier"], r["status"]) for r in
             s.conn.execute("SELECT claim_id, tier, status FROM claims").fetchall()}
    assert tiers["clm_b"] == (st.CONFIRMED, st.DONE)
    assert tiers["clm_c"] == (st.CORRECTED, st.DONE)
    assert tiers["clm_a"] == (None, st.PENDING)   # 반려 → 재처리 큐
    s.close()


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


def test_count_pending_scopes_to_uploaded_articles():
    s = _store()
    s.upsert_article("art_uploaded", "업로드", "2025-01-01", "", "u1", "b")
    s.upsert_article("art_existing", "기존", "2025-01-01", "", "u2", "b")
    s.enqueue_claim("clm_uploaded", "art_uploaded", "업로드 수치는 1%다.")
    s.enqueue_claim("clm_existing", "art_existing", "기존 수치는 2%다.")

    assert s.count_pending(["art_uploaded"]) == 1
    assert s.count_pending([]) == 0
    s.close()