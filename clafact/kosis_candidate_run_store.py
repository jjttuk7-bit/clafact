"""Research-only persistence for KOSIS candidate-search executions."""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any


class KosisCandidateRunStore:
    def __init__(self, path: str | Path) -> None:
        self.conn = sqlite3.connect(Path(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""CREATE TABLE IF NOT EXISTS kosis_candidate_run (
            run_id TEXT PRIMARY KEY, shadow_run_id TEXT, row_index INTEGER, sentence TEXT,
            query_text TEXT, created_at TEXT, candidates_json TEXT)""")
        self.conn.commit()

    def append(self, *, shadow_run_id: str, row_index: int, sentence: str, query: str,
               candidates: list[dict[str, Any]], created_at: str) -> str:
        run_id = f"candidate-{uuid.uuid4().hex[:16]}"
        with self.conn:
            self.conn.execute("INSERT INTO kosis_candidate_run VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, shadow_run_id, row_index, sentence, query, created_at,
                 json.dumps(candidates, ensure_ascii=False)))
        return run_id

    def list_csv_rows(self) -> list[dict[str, Any]]:
        records = self.conn.execute("SELECT * FROM kosis_candidate_run ORDER BY created_at DESC").fetchall()
        rows = []
        for record in records:
            for candidate in json.loads(record["candidates_json"]):
                rows.append({"candidate_run_id": record["run_id"], "shadow_run_id": record["shadow_run_id"],
                    "row_index": record["row_index"], "sentence": record["sentence"], "query": record["query_text"],
                    "created_at": record["created_at"], "rank": candidate["rank"], "table_id": candidate["table_id"],
                    "title": candidate["title"], "score": candidate["score"],
                    "reasons": " | ".join(candidate.get("reasons", [])), "penalties": " | ".join(candidate.get("penalties", []))})
        return rows

    def close(self) -> None: self.conn.close()
    def __enter__(self): return self
    def __exit__(self, *args: object) -> None: self.close()
