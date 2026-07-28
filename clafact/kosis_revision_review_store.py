"""Research-only review queue for Shadow mappings affected by KOSIS revisions."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clafact.kosis_revision_impact import KosisRevisionImpact


VALID_DECISIONS = frozenset({"approved", "hold", "ignored"})


@dataclass(frozen=True)
class KosisRevisionReview:
    review_id: str
    table_id: str
    shadow_run_id: str
    row_index: int
    before_snapshot_id: str
    after_snapshot_id: str
    detected_at: str
    status: str = "pending"
    note: str = ""
    decided_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "table_id": self.table_id,
            "shadow_run_id": self.shadow_run_id,
            "row_index": self.row_index,
            "before_snapshot_id": self.before_snapshot_id,
            "after_snapshot_id": self.after_snapshot_id,
            "detected_at": self.detected_at,
            "status": self.status,
            "note": self.note,
            "decided_at": self.decided_at,
        }


def _review_id(
    impact: KosisRevisionImpact, before_snapshot_id: str, after_snapshot_id: str
) -> str:
    seed = "|".join((
        impact.table_id, impact.shadow_run_id, str(impact.row_index),
        impact.period, impact.indicator, before_snapshot_id, after_snapshot_id,
    ))
    return f"revision-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"


class KosisRevisionReviewStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS kosis_revision_review (
            review_id TEXT PRIMARY KEY,
            table_id TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL
            )"""
        )
        self.conn.commit()

    def enqueue(
        self,
        impact: KosisRevisionImpact,
        *,
        before_snapshot_id: str,
        after_snapshot_id: str,
        detected_at: str,
    ) -> KosisRevisionReview:
        review = KosisRevisionReview(
            review_id=_review_id(impact, before_snapshot_id, after_snapshot_id),
            table_id=impact.table_id,
            shadow_run_id=impact.shadow_run_id,
            row_index=impact.row_index,
            before_snapshot_id=before_snapshot_id,
            after_snapshot_id=after_snapshot_id,
            detected_at=detected_at,
        )
        with self.conn:
            existing = self.conn.execute(
                "SELECT payload_json FROM kosis_revision_review WHERE review_id = ?",
                (review.review_id,),
            ).fetchone()
            if existing is None:
                self.conn.execute(
                    "INSERT INTO kosis_revision_review (review_id, table_id, status, payload_json) VALUES (?, ?, ?, ?)",
                    (review.review_id, review.table_id, review.status, json.dumps(review.as_dict(), ensure_ascii=False, sort_keys=True)),
                )
                return review
            payload = json.loads(existing["payload_json"])
            return KosisRevisionReview(**payload)

    def get(self, review_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM kosis_revision_review WHERE review_id = ?",
            (review_id,),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_for_table(self, table_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM kosis_revision_review WHERE table_id = ? ORDER BY rowid DESC",
            (table_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def decide(self, review_id: str, *, action: str, note: str, decided_at: str) -> None:
        if action not in VALID_DECISIONS:
            raise ValueError("action must be approved, hold, or ignored")
        existing = self.get(review_id)
        if existing is None:
            raise ValueError("review_id not found")
        existing.update({"status": action, "note": note, "decided_at": decided_at})
        with self.conn:
            self.conn.execute(
                "UPDATE kosis_revision_review SET status = ?, payload_json = ? WHERE review_id = ?",
                (action, json.dumps(existing, ensure_ascii=False, sort_keys=True), review_id),
            )

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KosisRevisionReviewStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
