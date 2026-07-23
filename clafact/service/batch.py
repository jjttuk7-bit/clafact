"""Batch Runner — 수집(ingest)과 처리(process)의 일 배치 (문서 25 §4).

기존 파이프라인(run.verify_sentence)을 심장으로 쓰고, 이 모듈은
큐 소비·멱등성·건별 격리·등급 분류(triage)·배치 이력만 담당한다.

지켜야 할 4원칙 (문서 25 §4.2):
  멱등성 — 같은 기사 두 번 넣어도 결과 하나 (stable id + 존재 검사)
  격리   — Claim 1건의 예외가 배치를 죽이지 않는다 (건별 try/except)
  예산   — KOSIS 호출 가드는 client 쪽(CachedKosisClient·CallBudget)이 담당
  폴백   — 실패는 FAILED 로 남기고 계속. 틀린 판정으로 새지 않는다
"""
from __future__ import annotations

import traceback
from pathlib import Path

from clafact import audit
from clafact.pipeline import detect
from clafact.pipeline.ingest import load_articles
from clafact.pipeline.run import ClaimResult, verify_sentence
from clafact.service import store as st
from clafact.service.store import Store


def triage(r: ClaimResult) -> str:
    """판정 결과 → 발행 등급 (문서 25 §5.1 게이트를 코드로).

    - 불일치는 예외 없이 사람 확인 (서비스에서 가장 위험한 발화)
    - 일치라도 신뢰도 high + 직접 조회(파생 계산 없음)만 자동확정
    - 판단불가는 사유와 함께 그대로 발행 (정직한 회피)
    """
    if r.label == "not_claim":
        return st.SKIPPED
    if r.label == "unverifiable":
        return st.UNVERIFIABLE
    if r.label == "mismatch":
        return st.NEEDS_REVIEW
    # match
    if r.confidence == "high" and not r.calculation:
        return st.AUTO_CONFIRMED
    return st.NEEDS_REVIEW


def ingest_file(store: Store, path: str | Path) -> dict:
    """기사 파일(JSONL/CSV) → 정제·문장분리(기존 ingest) → 기사 저장
    → 탐지 후보 문장만 Claim 큐잉. 전부 멱등."""
    articles = load_articles(path)
    stats = {"articles_seen": len(articles), "articles_new": 0,
             "claims_new": 0, "sentences_seen": 0}
    started = st.now_iso()
    for art in articles:
        aid = st.stable_article_id(art.url, art.title, art.date)
        if store.upsert_article(aid, art.title, art.date, art.section, art.url, art.body):
            stats["articles_new"] += 1
        for sent in art.sentences:
            stats["sentences_seen"] += 1
            if not detect.is_candidate(sent):   # 규칙 필터 = 재현율 담당 (2.2)
                continue
            if store.enqueue_claim(st.stable_claim_id(aid, sent), aid, sent):
                stats["claims_new"] += 1
    store.record_run("ingest", started, audit.code_version(), stats)
    return stats


def process_pending(store: Store, index=None, client=None,
                    limit: int | None = None, article_ids: list[str] | None = None,
                    claim_ids: list[str] | None = None, verify=None) -> dict:
    """PENDING Claim 을 순서대로 판정. verify 는 테스트 주입용
    (기본: 기존 파이프라인 verify_sentence)."""
    if verify is None:
        def verify(sentence, article_date):   # noqa: E306
            return verify_sentence(sentence, article_date, index, client)

    stats = {"processed": 0, "failed": 0,
             "by_tier": {}, "by_label": {}}
    started = st.now_iso()
    for row in store.fetch_pending(limit, article_ids=article_ids, claim_ids=claim_ids):
        try:
            r = verify(row["sentence"], row["article_date"])
            tier = triage(r)
            store.save_result(
                row["claim_id"], label=r.label, confidence=r.confidence, tier=tier,
                reason=r.reason, quantity=r.quantity, period=r.period,
                calculation=r.calculation, explanation=r.explanation,
                evidence=r.evidence, audit=r.audit)
            stats["processed"] += 1
            stats["by_tier"][tier] = stats["by_tier"].get(tier, 0) + 1
            stats["by_label"][r.label] = stats["by_label"].get(r.label, 0) + 1
        except Exception:
            # 격리: 이 건만 실패로 남기고 배치는 계속. (실패는 A4 의 원료다)
            store.mark_failed(row["claim_id"], traceback.format_exc(limit=3))
            stats["failed"] += 1
    store.record_run("process", started, audit.code_version(), stats)
    return stats
