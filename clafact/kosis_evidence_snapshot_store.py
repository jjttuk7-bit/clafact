"""Research-only SQLite store for immutable KOSIS evidence snapshots."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.kosis_evidence_snapshot import KosisEvidenceSnapshot


class KosisEvidenceSnapshotStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS kosis_evidence_snapshot (snapshot_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
        )
        self.conn.commit()

    def append(self, snapshot: KosisEvidenceSnapshot) -> bool:
        payload = json.dumps(snapshot.as_dict(), ensure_ascii=False, sort_keys=True)
        with self.conn:
            existing = self.conn.execute(
                "SELECT payload_json FROM kosis_evidence_snapshot WHERE snapshot_id = ?",
                (snapshot.snapshot_id,),
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload:
                    raise ValueError("different payload for existing snapshot_id")
                return False
            self.conn.execute(
                "INSERT INTO kosis_evidence_snapshot (snapshot_id, payload_json) VALUES (?, ?)",
                (snapshot.snapshot_id, payload),
            )
            return True

    def get(self, snapshot_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM kosis_evidence_snapshot WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_for_table(self, table_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM kosis_evidence_snapshot ORDER BY rowid DESC"
        ).fetchall()
        snapshots = [json.loads(row["payload_json"]) for row in rows]
        return [snapshot for snapshot in snapshots if snapshot["table_id"] == table_id]
    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KosisEvidenceSnapshotStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
