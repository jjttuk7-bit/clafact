"""KOSIS 통계표 근거 객체의 연구 전용 저장소."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.kosis_evidence import KosisEvidenceObject, build_evidence_id


_VOLATILE_EVIDENCE_FIELDS = frozenset({"retrieved_at", "snapshot_id"})


def _definition_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the stable evidence definition, excluding per-query provenance."""
    return {key: value for key, value in payload.items() if key not in _VOLATILE_EVIDENCE_FIELDS}


class KosisEvidenceStore:
    """Store exact evidence objects, not merely one object per KOSIS table."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        existing = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'kosis_evidence'"
        ).fetchone()
        if existing is not None:
            columns = {
                row["name"] for row in self.conn.execute("PRAGMA table_info(kosis_evidence)").fetchall()
            }
            if "evidence_id" not in columns:
                self._migrate_legacy_table()
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS kosis_evidence (
            evidence_id TEXT PRIMARY KEY,
            table_id TEXT NOT NULL,
            payload_json TEXT NOT NULL
            )"""
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kosis_evidence_table_id ON kosis_evidence (table_id)"
        )
        self.conn.commit()

    def _migrate_legacy_table(self) -> None:
        legacy_name = "kosis_evidence_legacy_table_id"
        self.conn.execute(f"ALTER TABLE kosis_evidence RENAME TO {legacy_name}")
        self.conn.execute(
            """CREATE TABLE kosis_evidence (
            evidence_id TEXT PRIMARY KEY,
            table_id TEXT NOT NULL,
            payload_json TEXT NOT NULL
            )"""
        )
        legacy_rows = self.conn.execute(
            f"SELECT payload_json FROM {legacy_name} ORDER BY rowid"
        ).fetchall()
        for row in legacy_rows:
            payload = json.loads(row["payload_json"])
            evidence_id = str(payload.get("evidence_id") or build_evidence_id(
                str(payload["table_id"]),
                str(payload["indicator"]),
                {str(key): str(value) for key, value in dict(payload.get("source_selection", {})).items()},
            ))
            payload["evidence_id"] = evidence_id
            self.conn.execute(
                "INSERT OR IGNORE INTO kosis_evidence (evidence_id, table_id, payload_json) VALUES (?, ?, ?)",
                (evidence_id, payload["table_id"], json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )

    def append(self, evidence: KosisEvidenceObject) -> bool:
        payload = json.dumps(evidence.as_dict(), ensure_ascii=False, sort_keys=True)
        with self.conn:
            existing = self.conn.execute(
                "SELECT payload_json FROM kosis_evidence WHERE evidence_id = ?", (evidence.evidence_id,)
            ).fetchone()
            if existing is not None:
                existing_payload = json.loads(existing["payload_json"])
                if _definition_payload(existing_payload) != _definition_payload(evidence.as_dict()):
                    raise ValueError("different evidence definition for existing evidence_id")
                return False
            self.conn.execute(
                "INSERT INTO kosis_evidence (evidence_id, table_id, payload_json) VALUES (?, ?, ?)",
                (evidence.evidence_id, evidence.table_id, payload),
            )
            return True

    def get(self, identifier: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM kosis_evidence WHERE evidence_id = ?", (identifier,)
        ).fetchone()
        if row is None:
            row = self.conn.execute(
                "SELECT payload_json FROM kosis_evidence WHERE table_id = ? ORDER BY rowid DESC LIMIT 1",
                (identifier,),
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
