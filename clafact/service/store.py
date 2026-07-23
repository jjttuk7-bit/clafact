"""Service Store — 기사·Claim·리뷰·배치 이력의 단일 저장소 (문서 25 §3 저장층).

v0 는 SQLite(stdlib) 지만 스키마·SQL 은 PostgreSQL 호환 부분집합만 쓴다
(TEXT/INTEGER, INSERT OR IGNORE 대신 존재 검사, AUTOINCREMENT 미사용)
— S4 에서 Postgres 로 갈 때 스키마 재설계가 없도록.

큐도 별도 인프라 없이 이 DB 다 — claims.status 가 곧 작업 큐다 (문서 25 §3:
"필요해질 때까지 단순하게").
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path

# claims.status — 작업 큐 상태
PENDING, DONE, FAILED, CLASSIFIED = "PENDING", "DONE", "FAILED", "CLASSIFIED"
# claims.tier — 발행 등급 (문서 25 §5.1)
AUTO_CONFIRMED = "AUTO_CONFIRMED"    # 사람 없이 발행 가능 (표본 감사 대상)
NEEDS_REVIEW = "NEEDS_REVIEW"        # 검증자 승인 전 발행 불가
UNVERIFIABLE = "UNVERIFIABLE"        # 판단불가 — 사유와 함께 그대로 발행
SKIPPED = "SKIPPED"                  # 주장 아님 — 발행물에 안 나감
# 리뷰 후 확정 등급
CONFIRMED, CORRECTED = "CONFIRMED", "CORRECTED"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    article_id  TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    date        TEXT NOT NULL DEFAULT '',
    section     TEXT NOT NULL DEFAULT '',
    url         TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
    claim_id     TEXT PRIMARY KEY,
    article_id   TEXT NOT NULL,
    sentence     TEXT NOT NULL,
    status       TEXT NOT NULL,
    source_type  TEXT NOT NULL DEFAULT 'UNCLASSIFIED',
    claim_type   TEXT NOT NULL DEFAULT '',
    route        TEXT NOT NULL DEFAULT 'KOSIS_RETRIEVAL',
    classification_reason TEXT NOT NULL DEFAULT '',
    label        TEXT,
    confidence   TEXT,
    tier         TEXT,
    reason       TEXT NOT NULL DEFAULT '',
    quantity     TEXT NOT NULL DEFAULT '',
    period       TEXT NOT NULL DEFAULT '',
    calculation  TEXT NOT NULL DEFAULT '',
    explanation  TEXT NOT NULL DEFAULT '',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    audit_json   TEXT NOT NULL DEFAULT '{}',
    error        TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    processed_at TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
    review_id  TEXT PRIMARY KEY,
    claim_id   TEXT NOT NULL,
    action     TEXT NOT NULL,
    reviewer   TEXT NOT NULL DEFAULT '',
    note       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batch_runs (
    run_id       TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    code_version TEXT NOT NULL DEFAULT '',
    stats_json   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_tier ON claims(tier);
CREATE INDEX IF NOT EXISTS idx_claims_article ON claims(article_id);
"""


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def stable_article_id(url: str, title: str, date: str) -> str:
    """재수집해도 같은 기사는 같은 ID — 멱등성의 뿌리 (문서 25 §4.2 원칙 1).

    ingest.load_articles 의 행번호 ID(A00001)는 파일이 바뀌면 흔들리므로
    서비스 층에서는 내용 기반 해시를 쓴다.
    """
    key = url.strip() or f"{title.strip()}|{date.strip()}"
    return "art_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def stable_claim_id(article_id: str, sentence: str) -> str:
    return "clm_" + hashlib.sha1(f"{article_id}|{sentence}".encode("utf-8")).hexdigest()[:16]


class Store:
    def __init__(self, db_path: str | Path):
        db_path = Path(db_path)
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate_schema()
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _migrate_schema(self) -> None:
        """기존 서비스 DB에 출처 분류 열을 안전하게 보강한다."""
        existing = {row["name"] for row in self.conn.execute("PRAGMA table_info(claims)")}
        additions = {
            "source_type": "TEXT NOT NULL DEFAULT 'UNCLASSIFIED'",
            "claim_type": "TEXT NOT NULL DEFAULT ''",
            "route": "TEXT NOT NULL DEFAULT 'LEGACY_UNCLASSIFIED'",
            "classification_reason": "TEXT NOT NULL DEFAULT ''",
        }
        for name, definition in additions.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE claims ADD COLUMN {name} {definition}")
        self.conn.execute(
            "UPDATE claims SET route='LEGACY_UNCLASSIFIED' "
            "WHERE route IS NULL OR route=''"
        )
    # ── 적재 (멱등) ──────────────────────────────────────────────

    def upsert_article(self, article_id: str, title: str, date: str,
                       section: str, url: str, body: str) -> bool:
        """신규면 True. 이미 있으면 건드리지 않는다 (원본은 불변)."""
        cur = self.conn.execute(
            "SELECT 1 FROM articles WHERE article_id = ?", (article_id,))
        if cur.fetchone():
            return False
        self.conn.execute(
            "INSERT INTO articles (article_id, title, date, section, url, body, ingested_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (article_id, title, date, section, url, body, now_iso()))
        self.conn.commit()
        return True

    def enqueue_claim(self, claim_id: str, article_id: str, sentence: str,
                      audit: dict | None = None, classification: dict | None = None) -> bool:
        """신규 Claim을 출처 라우팅과 함께 저장한다."""
        if self.conn.execute("SELECT 1 FROM claims WHERE claim_id = ?", (claim_id,)).fetchone():
            return False
        classification = classification or {}
        route = classification.get("route", "KOSIS_RETRIEVAL")
        status = PENDING if route == "KOSIS_RETRIEVAL" else CLASSIFIED
        self.conn.execute(
            "INSERT INTO claims (claim_id, article_id, sentence, status, source_type, claim_type, route, "
            "classification_reason, audit_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (claim_id, article_id, sentence, status,
             classification.get("source_type", "UNCLASSIFIED"),
             classification.get("claim_type", ""), route,
             classification.get("reason", ""), json.dumps(audit or {}, ensure_ascii=False), now_iso()),
        )
        self.conn.commit()
        return True    # ── 큐 소비 ─────────────────────────────────────────────────

    def fetch_pending(self, limit: int | None = None,
                      article_ids: list[str] | None = None,
                      claim_ids: list[str] | None = None) -> list[sqlite3.Row]:
        sql = ("SELECT c.claim_id, c.sentence, c.article_id, a.date AS article_date"
               " FROM claims c JOIN articles a ON a.article_id = c.article_id"
               " WHERE c.status = ? AND c.route = ?")
        params: list[str] = [PENDING, "KOSIS_RETRIEVAL"]
        if article_ids is not None:
            if not article_ids:
                return []
            placeholders = ", ".join("?" for _ in article_ids)
            sql += f" AND c.article_id IN ({placeholders})"
            params.extend(article_ids)
        if claim_ids is not None:
            if not claim_ids:
                return []
            placeholders = ", ".join("?" for _ in claim_ids)
            sql += f" AND c.claim_id IN ({placeholders})"
            params.extend(claim_ids)
        sql += " ORDER BY c.created_at, c.claim_id"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.conn.execute(sql, params).fetchall()

    def count_pending(self, article_ids: list[str] | None = None) -> int:
        sql = "SELECT COUNT(*) AS n FROM claims WHERE status = ? AND route = ?"
        params: list[str] = [PENDING, "KOSIS_RETRIEVAL"]
        if article_ids is not None:
            if not article_ids:
                return 0
            placeholders = ", ".join("?" for _ in article_ids)
            sql += f" AND article_id IN ({placeholders})"
            params.extend(article_ids)
        return int(self.conn.execute(sql, params).fetchone()["n"])
    def _upload_result_filter(self, article_ids: list[str], *, status: str | None = None,
                              label: str | None = None, route: str | None = None, search: str = "") -> tuple[str, list[str]]:
        if not article_ids:
            return "", []
        placeholders = ", ".join("?" for _ in article_ids)
        clauses = [f"c.article_id IN ({placeholders})"]
        params = list(article_ids)
        if status:
            clauses.append("c.status = ?")
            params.append(status)
        if label:
            clauses.append("c.label = ?")
            params.append(label)
        if route:
            clauses.append("c.route = ?")
            params.append(route)
        if search.strip():
            clauses.append("c.sentence LIKE ?")
            params.append(f"%{search.strip()}%")
        return " WHERE " + " AND ".join(clauses), params

    def count_upload_results(self, article_ids: list[str], *, status: str | None = None,
                             label: str | None = None, route: str | None = None, search: str = "") -> int:
        """선택 업로드에서 필터에 맞는 Claim 수를 반환한다."""
        where, params = self._upload_result_filter(article_ids, status=status, label=label, route=route, search=search)
        if not where:
            return 0
        row = self.conn.execute("SELECT COUNT(*) AS n FROM claims c" + where, params).fetchone()
        return int(row["n"])

    def fetch_upload_results(self, article_ids: list[str], *, status: str | None = None,
                             label: str | None = None, route: str | None = None, search: str = "",
                             limit: int | None = None, offset: int = 0) -> list[sqlite3.Row]:
        """선택한 업로드의 기사와 Claim 판정 원본을 필터·페이지 단위로 반환한다."""
        where, params = self._upload_result_filter(article_ids, status=status, label=label, route=route, search=search)
        if not where:
            return []
        sql = (
            "SELECT c.*, a.title, a.date AS article_date, a.section, a.url "
            "FROM claims c JOIN articles a ON a.article_id = c.article_id"
            + where + " ORDER BY a.date DESC, a.title, c.created_at, c.claim_id"
        )
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([int(limit), max(0, int(offset))])
        return self.conn.execute(sql, params).fetchall()

    def save_result(self, claim_id: str, *, label: str, confidence: str | None,
                    tier: str, reason: str = "", quantity: str = "", period: str = "",
                    calculation: str = "", explanation: str = "",
                    evidence: dict | None = None, audit: dict | None = None) -> None:
        self.conn.execute(
            "UPDATE claims SET status=?, label=?, confidence=?, tier=?, reason=?,"
            " quantity=?, period=?, calculation=?, explanation=?,"
            " evidence_json=?, audit_json=?, error='', processed_at=?"
            " WHERE claim_id=?",
            (DONE, label, confidence, tier, reason, quantity, period, calculation,
             explanation, json.dumps(evidence or {}, ensure_ascii=False),
             json.dumps(audit or {}, ensure_ascii=False), now_iso(), claim_id))
        self.conn.commit()

    def mark_failed(self, claim_id: str, error: str) -> None:
        """Claim 1건의 실패를 격리한다 — 배치는 계속 (문서 25 §4.2 원칙 2)."""
        self.conn.execute(
            "UPDATE claims SET status=?, error=?, processed_at=? WHERE claim_id=?",
            (FAILED, error[:500], now_iso(), claim_id))
        self.conn.commit()

    # ── 리뷰 (HITL, 문서 25 §5) ──────────────────────────────────

    def review_queue(self) -> list[sqlite3.Row]:
        """위험한 것부터: 불일치 → low → medium → high (WF-2 정렬 그대로)."""
        return self.conn.execute(
            "SELECT * FROM claims WHERE tier = ? ORDER BY"
            " CASE WHEN label = 'mismatch' THEN 0 ELSE 1 END,"
            " CASE confidence WHEN 'low' THEN 0 WHEN 'medium' THEN 1"
            "  WHEN 'high' THEN 2 ELSE 3 END,"
            " created_at", (NEEDS_REVIEW,)).fetchall()

    def apply_review(self, claim_id: str, action: str,
                     reviewer: str = "", note: str = "") -> None:
        """approve → CONFIRMED / correct → CORRECTED(+A4 연계는 배치 층에서)
        / reject → PENDING 재처리 (상태 머신 IN_REVIEW 분기와 동일)."""
        if action not in ("approve", "correct", "reject"):
            raise ValueError(f"알 수 없는 리뷰 액션: {action}")
        self.conn.execute(
            "INSERT INTO reviews (review_id, claim_id, action, reviewer, note, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            ("rev_" + uuid.uuid4().hex[:12], claim_id, action, reviewer, note, now_iso()))
        if action == "approve":
            self.conn.execute("UPDATE claims SET tier=? WHERE claim_id=?",
                              (CONFIRMED, claim_id))
        elif action == "correct":
            self.conn.execute("UPDATE claims SET tier=? WHERE claim_id=?",
                              (CORRECTED, claim_id))
        else:  # reject → 재처리 큐로
            self.conn.execute(
                "UPDATE claims SET status=?, tier=NULL, label=NULL, confidence=NULL"
                " WHERE claim_id=?", (PENDING, claim_id))
        self.conn.commit()

    # ── 배치 이력·리포트 ─────────────────────────────────────────

    def record_run(self, kind: str, started_at: str, code_version: str,
                   stats: dict) -> str:
        run_id = "run_" + uuid.uuid4().hex[:12]
        self.conn.execute(
            "INSERT INTO batch_runs (run_id, kind, started_at, finished_at,"
            " code_version, stats_json) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, kind, started_at, now_iso(), code_version,
             json.dumps(stats, ensure_ascii=False)))
        self.conn.commit()
        return run_id

    def summary(self) -> dict:
        def _counts(col: str) -> dict:
            rows = self.conn.execute(
                f"SELECT {col} AS k, COUNT(*) AS n FROM claims"
                f" WHERE {col} IS NOT NULL GROUP BY {col}").fetchall()
            return {r["k"]: r["n"] for r in rows}
        n_articles = self.conn.execute("SELECT COUNT(*) AS n FROM articles").fetchone()["n"]
        last = self.conn.execute(
            "SELECT * FROM batch_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        return {
            "articles": n_articles,
            "claims_by_status": _counts("status"),
            "claims_by_label": _counts("label"),
            "claims_by_tier": _counts("tier"),
            "review_queue": len(self.review_queue()),
            "last_run": dict(last) if last else None,
        }
