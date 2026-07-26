"""Append-only SQLite storage for verification-lab research results."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence


RUN_COLUMNS = (
    "run_id",
    "created_at",
    "article_hash",
    "article_title",
    "article_date",
    "provider",
    "model",
    "prompt_version",
    "python_ms",
    "hcx_ms",
    "total_ms",
    "hcx_calls",
    "source_row_count",
    "sentence_count",
)

SENTENCE_COLUMNS = (
    "run_id",
    "sentence_index",
    "sentence_hash",
    "sentence_text",
    "python_candidate",
    "python_reason",
    "hcx_status",
    "hcx_candidate",
    "hcx_reason",
    "evidence_status",
    "disagreement_class",
    "human_label",
    "review_note",
    "reviewed_at",
)

REVIEW_LABELS = frozenset({"true_candidate", "false_positive", "hold"})


class ExperimentStore:
    """Research-only store that has no dependency on the operating database."""

    def __init__(self, path: str | Path) -> None:
        database = str(path)
        if database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(database)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _initialize(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS experiment_runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                article_hash TEXT NOT NULL,
                article_title TEXT,
                article_date TEXT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                python_ms INTEGER NOT NULL,
                hcx_ms INTEGER NOT NULL,
                total_ms INTEGER NOT NULL,
                hcx_calls INTEGER NOT NULL,
                source_row_count INTEGER NOT NULL,
                sentence_count INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS experiment_sentences (
                run_id TEXT NOT NULL,
                sentence_index INTEGER NOT NULL,
                sentence_hash TEXT NOT NULL,
                sentence_text TEXT NOT NULL,
                python_candidate INTEGER NOT NULL CHECK (python_candidate IN (0, 1)),
                python_reason TEXT NOT NULL,
                hcx_status TEXT NOT NULL,
                hcx_candidate INTEGER CHECK (hcx_candidate IN (0, 1) OR hcx_candidate IS NULL),
                hcx_reason TEXT NOT NULL,
                evidence_status TEXT,
                disagreement_class TEXT NOT NULL,
                human_label TEXT CHECK (
                    human_label IN ('true_candidate', 'false_positive', 'hold')
                    OR human_label IS NULL
                ),
                review_note TEXT,
                reviewed_at TEXT,
                PRIMARY KEY (run_id, sentence_index),
                FOREIGN KEY (run_id) REFERENCES experiment_runs(run_id)
            );
            """
        )

    def append_run(
        self,
        run: Mapping[str, Any],
        sentences: Sequence[Mapping[str, Any]],
    ) -> None:
        run_values = tuple(run[column] for column in RUN_COLUMNS)
        run_placeholders = ", ".join("?" for _ in RUN_COLUMNS)
        run_columns = ", ".join(RUN_COLUMNS)
        sentence_placeholders = ", ".join("?" for _ in SENTENCE_COLUMNS)
        sentence_columns = ", ".join(SENTENCE_COLUMNS)
        sentence_rows = [
            tuple(
                self._sentence_value(run["run_id"], sentence, column)
                for column in SENTENCE_COLUMNS
            )
            for sentence in sentences
        ]

        with self.conn:
            self.conn.execute(
                f"INSERT INTO experiment_runs ({run_columns}) VALUES ({run_placeholders})",
                run_values,
            )
            self.conn.executemany(
                f"INSERT INTO experiment_sentences ({sentence_columns}) "
                f"VALUES ({sentence_placeholders})",
                sentence_rows,
            )

    @staticmethod
    def _sentence_value(
        run_id: str,
        sentence: Mapping[str, Any],
        column: str,
    ) -> Any:
        if column == "run_id":
            return run_id
        if column in {"human_label", "review_note", "reviewed_at"}:
            return sentence.get(column)
        return sentence[column]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM experiment_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def get_sentences(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM experiment_sentences
            WHERE run_id = ?
            ORDER BY sentence_index
            """,
            (run_id,),
        ).fetchall()
        return [self._sentence_dict(row) for row in rows]

    @staticmethod
    def _sentence_dict(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["python_candidate"] = bool(result["python_candidate"])
        if result["hcx_candidate"] is not None:
            result["hcx_candidate"] = bool(result["hcx_candidate"])
        return result

    def update_review(
        self,
        run_id: str,
        sentence_index: int,
        *,
        human_label: str,
        review_note: str | None,
        reviewed_at: str,
    ) -> None:
        if human_label not in REVIEW_LABELS:
            raise ValueError(
                "human_label must be true_candidate, false_positive, or hold"
            )
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE experiment_sentences
                SET human_label = ?, review_note = ?, reviewed_at = ?
                WHERE run_id = ? AND sentence_index = ?
                """,
                (
                    human_label,
                    review_note,
                    reviewed_at,
                    run_id,
                    sentence_index,
                ),
            )
        if cursor.rowcount == 0:
            raise KeyError((run_id, sentence_index))

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ExperimentStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
