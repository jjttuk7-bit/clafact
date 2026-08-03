"""Research persistence for confirmed reusable KOSIS Semantic Cards."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from clafact.kosis_semantic_card import SemanticCard


class KosisSemanticCardStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS kosis_semantic_card (table_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
        )
        self.conn.commit()

    def upsert(self, card: SemanticCard) -> bool:
        if not card.confirmed_at:
            raise ValueError("only confirmed Semantic Cards can be persisted")
        payload = json.dumps(card.as_dict(), ensure_ascii=False, sort_keys=True)
        with self.conn:
            existing = self.conn.execute(
                "SELECT payload_json FROM kosis_semantic_card WHERE table_id = ?", (card.table_id,)
            ).fetchone()
            self.conn.execute(
                "INSERT INTO kosis_semantic_card (table_id, payload_json) VALUES (?, ?) "
                "ON CONFLICT(table_id) DO UPDATE SET payload_json = excluded.payload_json",
                (card.table_id, payload),
            )
        return existing is None

    def get(self, table_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM kosis_semantic_card WHERE table_id = ?", (table_id,)
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT payload_json FROM kosis_semantic_card ORDER BY rowid DESC").fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM kosis_semantic_card").fetchone()[0])

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KosisSemanticCardStore":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
