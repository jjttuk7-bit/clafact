"""Shadow Lab 전용의 append-only 연구 SQLite 저장소."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence


RUN_COLUMNS = (
    "run_id", "created_at", "input_hash", "policy_json", "baseline_name",
    "shadow_name", "status", "summary_json",
)
ROW_COLUMNS = (
    "run_id", "row_index", "sentence", "baseline_json", "shadow_json",
    "review_state", "risk_reasons_json",
)
REVIEW_ACTIONS = frozenset({"approve", "correct", "hold"})


class ShadowStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _initialize(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS shadow_runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                policy_json TEXT NOT NULL,
                baseline_name TEXT NOT NULL,
                shadow_name TEXT NOT NULL,
                status TEXT NOT NULL,
                summary_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shadow_rows (
                run_id TEXT NOT NULL,
                row_index INTEGER NOT NULL,
                sentence TEXT NOT NULL,
                baseline_json TEXT NOT NULL,
                shadow_json TEXT NOT NULL,
                review_state TEXT NOT NULL CHECK (review_state IN ('auto', 'needs_review', 'reviewed', 'hold')),
                risk_reasons_json TEXT NOT NULL,
                PRIMARY KEY (run_id, row_index),
                FOREIGN KEY (run_id) REFERENCES shadow_runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS shadow_reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                row_index INTEGER NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('approve', 'correct', 'hold')),
                note TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                FOREIGN KEY (run_id, row_index) REFERENCES shadow_rows(run_id, row_index)
            );
            """
        )
        self.conn.commit()

    def append_run(self, run: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> bool:
        if not rows:
            raise ValueError("shadow run must contain at least one row")
        run_id = str(run["run_id"])
        expected_run = {column: run[column] for column in RUN_COLUMNS}
        expected_rows = [
            {**{column: row[column] for column in ROW_COLUMNS if column != "run_id"}, "run_id": run_id}
            for row in rows
        ]
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            existing = self.conn.execute(
                "SELECT * FROM shadow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing is not None:
                existing_run = {column: existing[column] for column in RUN_COLUMNS}
                existing_rows = [dict(row) for row in self.conn.execute(
                    "SELECT * FROM shadow_rows WHERE run_id = ? ORDER BY row_index", (run_id,)
                ).fetchall()]
                if existing_run != expected_run or existing_rows != expected_rows:
                    raise ValueError("different payload for existing run_id")
                self.conn.commit()
                return False

            self.conn.execute(
                f"INSERT INTO shadow_runs ({', '.join(RUN_COLUMNS)}) VALUES ({', '.join('?' for _ in RUN_COLUMNS)})",
                tuple(expected_run[column] for column in RUN_COLUMNS),
            )
            self.conn.executemany(
                f"INSERT INTO shadow_rows ({', '.join(ROW_COLUMNS)}) VALUES ({', '.join('?' for _ in ROW_COLUMNS)})",
                [tuple(row[column] for column in ROW_COLUMNS) for row in expected_rows],
            )
            self.conn.commit()
            return True
        except BaseException:
            self.conn.rollback()
            raise

    def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        return [dict(row) for row in self.conn.execute(
            "SELECT * FROM shadow_runs ORDER BY created_at DESC, run_id DESC LIMIT ?", (limit,)
        ).fetchall()]
    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM shadow_runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row is not None else None

    def list_rows(self, run_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(
            "SELECT * FROM shadow_rows WHERE run_id = ? ORDER BY row_index", (run_id,)
        ).fetchall()]

    def list_review_rows(self, run_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(
            "SELECT * FROM shadow_rows WHERE run_id = ? AND review_state IN ('needs_review', 'reviewed', 'hold') ORDER BY row_index",
            (run_id,),
        ).fetchall()]

    def list_reviews(self, run_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(
            "SELECT review_id, run_id, row_index, action, note, reviewed_at "
            "FROM shadow_reviews WHERE run_id = ? ORDER BY review_id",
            (run_id,),
        ).fetchall()]

    def append_review(self, run_id: str, row_index: int, *, action: str, note: str, reviewed_at: str) -> bool:
        if action not in REVIEW_ACTIONS:
            raise ValueError(f"unknown review action: {action}")
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                "SELECT review_state FROM shadow_rows WHERE run_id = ? AND row_index = ?", (run_id, row_index)
            ).fetchone()
            if row is None:
                raise KeyError((run_id, row_index))
            existing = self.conn.execute(
                "SELECT action, note, reviewed_at FROM shadow_reviews WHERE run_id = ? AND row_index = ? ORDER BY review_id DESC LIMIT 1",
                (run_id, row_index),
            ).fetchone()
            requested = (action, note, reviewed_at)
            if existing is not None and tuple(existing) == requested:
                self.conn.commit()
                return False
            self.conn.execute(
                "INSERT INTO shadow_reviews (run_id, row_index, action, note, reviewed_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, row_index, action, note, reviewed_at),
            )
            state = "hold" if action == "hold" else "reviewed"
            self.conn.execute(
                "UPDATE shadow_rows SET review_state = ? WHERE run_id = ? AND row_index = ?",
                ("reviewed", run_id, row_index),
            )
            self.conn.commit()
            return True
        except BaseException:
            self.conn.rollback()
            raise

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ShadowStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
