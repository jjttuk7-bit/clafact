"""Persist KOSIS-Shadow mappings separately from operating verdicts."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.kosis_shadow_mapping import KosisShadowMapping


class KosisShadowMappingStore:
    """SQLite store for research-only mapping history."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS kosis_shadow_mapping (
            shadow_run_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            table_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (shadow_run_id, row_index, table_id)
            )"""
        )
        self.conn.commit()

    def append(self, mapping: KosisShadowMapping) -> bool:
        payload = json.dumps(mapping.as_dict(), ensure_ascii=False, sort_keys=True)
        with self.conn:
            existing = self.conn.execute(
                "SELECT payload_json FROM kosis_shadow_mapping WHERE shadow_run_id = ? AND row_index = ? AND table_id = ?",
                (mapping.shadow_run_id, mapping.row_index, mapping.table_id),
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload:
                    raise ValueError("different payload for existing mapping")
                return False
            self.conn.execute(
                "INSERT INTO kosis_shadow_mapping (shadow_run_id, row_index, table_id, payload_json) VALUES (?, ?, ?, ?)",
                (mapping.shadow_run_id, mapping.row_index, mapping.table_id, payload),
            )
            return True

    def list_for_run(self, shadow_run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM kosis_shadow_mapping WHERE shadow_run_id = ? ORDER BY row_index, table_id",
            (shadow_run_id,),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KosisShadowMappingStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()