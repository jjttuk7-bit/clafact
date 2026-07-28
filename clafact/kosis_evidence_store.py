"""KOSIS 통계표 근거 객체의 연구 전용 저장소."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.kosis_evidence import KosisEvidenceObject


class KosisEvidenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS kosis_evidence (table_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
        )
        self.conn.commit()

    def append(self, evidence: KosisEvidenceObject) -> bool:
        payload = json.dumps(evidence.as_dict(), ensure_ascii=False, sort_keys=True)
        with self.conn:
            existing = self.conn.execute(
                "SELECT payload_json FROM kosis_evidence WHERE table_id = ?", (evidence.table_id,)
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload:
                    raise ValueError("different payload for existing table_id")
                return False
            self.conn.execute(
                "INSERT INTO kosis_evidence (table_id, payload_json) VALUES (?, ?)",
                (evidence.table_id, payload),
            )
            return True

    def get(self, table_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM kosis_evidence WHERE table_id = ?", (table_id,)
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM kosis_evidence ORDER BY rowid DESC"
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KosisEvidenceStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
