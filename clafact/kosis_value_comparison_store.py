"""Persist numerical KOSIS comparisons as immutable Shadow research records."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.kosis_value_comparison import KosisValueComparison


class KosisValueComparisonStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS kosis_value_comparison (
            shadow_run_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            evidence_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (shadow_run_id, row_index, evidence_id, snapshot_id)
            )"""
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kosis_value_comparison_run "
            "ON kosis_value_comparison (shadow_run_id, row_index)"
        )
        self.conn.commit()

    def append(
        self,
        *,
        shadow_run_id: str,
        row_index: int,
        evidence_id: str,
        comparison: KosisValueComparison,
    ) -> bool:
        if not shadow_run_id.strip() or not evidence_id.strip():
            raise ValueError("shadow_run_id and evidence_id are required")
        payload = {
            "shadow_run_id": shadow_run_id,
            "row_index": row_index,
            "evidence_id": evidence_id,
            **comparison.as_dict(),
        }
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        key = (shadow_run_id, row_index, evidence_id, comparison.snapshot_id)
        with self.conn:
            existing = self.conn.execute(
                """SELECT payload_json FROM kosis_value_comparison
                WHERE shadow_run_id = ? AND row_index = ? AND evidence_id = ? AND snapshot_id = ?""",
                key,
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload_json:
                    raise ValueError("different payload for existing value comparison")
                return False
            self.conn.execute(
                """INSERT INTO kosis_value_comparison
                (shadow_run_id, row_index, evidence_id, snapshot_id, payload_json)
                VALUES (?, ?, ?, ?, ?)""",
                (*key, payload_json),
            )
            return True

    def list_for_run(self, shadow_run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT payload_json FROM kosis_value_comparison
            WHERE shadow_run_id = ? ORDER BY row_index, rowid DESC""",
            (shadow_run_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def list_for_evidence(self, evidence_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT payload_json FROM kosis_value_comparison
            WHERE evidence_id = ? ORDER BY rowid DESC""",
            (evidence_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KosisValueComparisonStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
