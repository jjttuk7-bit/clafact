"""Persist immutable Claim completion records for Shadow runs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping


class ClaimCompletionStore:
    """Store one completed Claim for each Shadow sentence/evidence/snapshot key."""

    def __init__(self, path: str | Path) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS claim_completion (
            shadow_run_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            evidence_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (shadow_run_id, row_index, evidence_id, snapshot_id)
            )"""
        )

    def append(self, record: Mapping[str, Any]) -> bool:
        """Append an immutable record, returning false when the exact record exists."""
        required = ("shadow_run_id", "row_index", "evidence_id", "snapshot_id")
        if any(not str(record.get(key, "")).strip() for key in required):
            raise ValueError("completed Claim requires Shadow, row, evidence, and snapshot identifiers")
        payload_json = json.dumps(dict(record), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        key = tuple(record[key] for key in required)
        with self.conn:
            existing = self.conn.execute(
                """SELECT payload_json FROM claim_completion
                WHERE shadow_run_id = ? AND row_index = ? AND evidence_id = ? AND snapshot_id = ?""",
                key,
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload_json:
                    raise ValueError("different payload for existing completed Claim")
                return False
            self.conn.execute(
                """INSERT INTO claim_completion
                (shadow_run_id, row_index, evidence_id, snapshot_id, payload_json)
                VALUES (?, ?, ?, ?, ?)""",
                (*key, payload_json),
            )
        return True

    def list_for_run(self, shadow_run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT payload_json FROM claim_completion
            WHERE shadow_run_id = ? ORDER BY row_index, rowid""",
            (shadow_run_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ClaimCompletionStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
