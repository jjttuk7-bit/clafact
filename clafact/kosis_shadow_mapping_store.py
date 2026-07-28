"""Persist KOSIS-Shadow mappings separately from operating verdicts."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.kosis_shadow_mapping import KosisShadowMapping


class KosisShadowMappingStore:
    """SQLite store for research-only exact-evidence mapping history."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        existing = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'kosis_shadow_mapping'"
        ).fetchone()
        if existing is not None:
            columns = {
                row["name"]
                for row in self.conn.execute("PRAGMA table_info(kosis_shadow_mapping)").fetchall()
            }
            if "evidence_id" not in columns:
                self._migrate_legacy_table()
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS kosis_shadow_mapping (
            shadow_run_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            evidence_id TEXT NOT NULL,
            table_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (shadow_run_id, row_index, evidence_id)
            )"""
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kosis_mapping_table_id ON kosis_shadow_mapping (table_id)"
        )
        self.conn.commit()

    def _migrate_legacy_table(self) -> None:
        legacy_name = "kosis_shadow_mapping_legacy_table_id"
        self.conn.execute(f"ALTER TABLE kosis_shadow_mapping RENAME TO {legacy_name}")
        self.conn.execute(
            """CREATE TABLE kosis_shadow_mapping (
            shadow_run_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            evidence_id TEXT NOT NULL,
            table_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (shadow_run_id, row_index, evidence_id)
            )"""
        )
        rows = self.conn.execute(f"SELECT payload_json FROM {legacy_name} ORDER BY rowid").fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            table_id = str(payload["table_id"])
            evidence_id = str(payload.get("evidence_id") or table_id)
            payload["evidence_id"] = evidence_id
            self.conn.execute(
                """INSERT OR IGNORE INTO kosis_shadow_mapping
                (shadow_run_id, row_index, evidence_id, table_id, payload_json) VALUES (?, ?, ?, ?, ?)""",
                (
                    payload["shadow_run_id"], int(payload["row_index"]), evidence_id, table_id,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            )

    def append(self, mapping: KosisShadowMapping) -> bool:
        payload = json.dumps(mapping.as_dict(), ensure_ascii=False, sort_keys=True)
        evidence_id = mapping.resolved_evidence_id
        with self.conn:
            existing = self.conn.execute(
                """SELECT payload_json FROM kosis_shadow_mapping
                WHERE shadow_run_id = ? AND row_index = ? AND evidence_id = ?""",
                (mapping.shadow_run_id, mapping.row_index, evidence_id),
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload:
                    raise ValueError("different payload for existing evidence mapping")
                return False
            self.conn.execute(
                """INSERT INTO kosis_shadow_mapping
                (shadow_run_id, row_index, evidence_id, table_id, payload_json) VALUES (?, ?, ?, ?, ?)""",
                (mapping.shadow_run_id, mapping.row_index, evidence_id, mapping.table_id, payload),
            )
            return True

    def list_for_run(self, shadow_run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM kosis_shadow_mapping WHERE shadow_run_id = ? ORDER BY row_index, evidence_id",
            (shadow_run_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def list_for_table(self, table_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM kosis_shadow_mapping WHERE table_id = ? ORDER BY shadow_run_id, row_index",
            (table_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def list_for_evidence(self, evidence_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM kosis_shadow_mapping WHERE evidence_id = ? ORDER BY shadow_run_id, row_index",
            (evidence_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KosisShadowMappingStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
