"""Persistence for reviewed Claim Cards keyed by parent sentence and atomic Claim."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.claim_card import ClaimCard


class ClaimCardStore:
    """Store reviewed Claims selected from each Shadow run sentence."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS claim_card (
            shadow_run_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            claim_index INTEGER NOT NULL DEFAULT 1,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (shadow_run_id, row_index, claim_index)
            )"""
        )
        columns = {
            str(row["name"])
            for row in self.conn.execute("PRAGMA table_info(claim_card)").fetchall()
        }
        if "claim_index" not in columns:
            self._migrate_legacy_schema()
        self.conn.commit()

    def _migrate_legacy_schema(self) -> None:
        """Preserve old one-card-per-sentence rows as atomic Claim #1."""
        with self.conn:
            self.conn.execute("ALTER TABLE claim_card RENAME TO claim_card_legacy")
            self.conn.execute(
                """CREATE TABLE claim_card (
                shadow_run_id TEXT NOT NULL,
                row_index INTEGER NOT NULL,
                claim_index INTEGER NOT NULL DEFAULT 1,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (shadow_run_id, row_index, claim_index)
                )"""
            )
            self.conn.execute(
                """INSERT INTO claim_card (shadow_run_id, row_index, claim_index, payload_json)
                SELECT shadow_run_id, row_index, 1, payload_json FROM claim_card_legacy"""
            )
            self.conn.execute("DROP TABLE claim_card_legacy")

    def upsert(
        self, shadow_run_id: str, row_index: int, card: ClaimCard, *, claim_index: int = 1,
    ) -> bool:
        if not card.confirmed_at:
            raise ValueError("only confirmed Claim Cards can be persisted")
        payload = json.dumps(card.as_dict(), ensure_ascii=False, sort_keys=True)
        with self.conn:
            existing = self.conn.execute(
                """SELECT payload_json FROM claim_card
                WHERE shadow_run_id = ? AND row_index = ? AND claim_index = ?""",
                (shadow_run_id, row_index, claim_index),
            ).fetchone()
            self.conn.execute(
                """INSERT INTO claim_card (shadow_run_id, row_index, claim_index, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(shadow_run_id, row_index, claim_index)
                DO UPDATE SET payload_json = excluded.payload_json""",
                (shadow_run_id, row_index, claim_index, payload),
            )
        return existing is None

    def get(self, shadow_run_id: str, row_index: int, *, claim_index: int = 1) -> dict[str, Any] | None:
        row = self.conn.execute(
            """SELECT payload_json FROM claim_card
            WHERE shadow_run_id = ? AND row_index = ? AND claim_index = ?""",
            (shadow_run_id, row_index, claim_index),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_for_run(self, shadow_run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM claim_card WHERE shadow_run_id = ? ORDER BY row_index, claim_index",
            (shadow_run_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ClaimCardStore":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
