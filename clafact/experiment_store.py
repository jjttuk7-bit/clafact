"""Append-only SQLite storage for verification-lab research results."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from clafact.experiment_analysis import (
    HCX_ERROR,
    P_MINUS_H_MINUS,
    P_MINUS_H_PLUS,
    P_PLUS_H_MINUS,
    P_PLUS_H_PLUS,
    classify_disagreement,
)


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
DISAGREEMENT_CLASSES = frozenset(
    {
        P_PLUS_H_PLUS,
        P_PLUS_H_MINUS,
        P_MINUS_H_PLUS,
        P_MINUS_H_MINUS,
        HCX_ERROR,
    }
)


class ExperimentStore:
    """Research-only store that has no dependency on the operating database."""

    def __init__(self, path: str | Path) -> None:
        database = str(path)
        if database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(database, timeout=30.0)
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
                disagreement_class TEXT NOT NULL CHECK (
                    disagreement_class IN ('P+/H+', 'P+/H-', 'P-/H+', 'P-/H-', 'HCX_ERROR')
                ),
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
        if run["sentence_count"] != len(sentences):
            raise ValueError("sentence_count must equal the number of sentence rows")
        for sentence in sentences:
            self._validate_sentence(sentence)

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

    def append_run_idempotent(
        self,
        run: Mapping[str, Any],
        sentences: Sequence[Mapping[str, Any]],
    ) -> bool:
        """Atomically insert one run, or verify an identical concurrent insert."""
        if run["sentence_count"] != len(sentences):
            raise ValueError("sentence_count must equal the number of sentence rows")
        for sentence in sentences:
            self._validate_sentence(sentence)

        run_id = str(run["run_id"])
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            existing_run_row = self.conn.execute(
                "SELECT * FROM experiment_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing_run_row is not None:
                existing_run = dict(existing_run_row)
                expected_run = {column: run[column] for column in RUN_COLUMNS}
                existing_sentence_rows = self.conn.execute(
                    """
                    SELECT * FROM experiment_sentences
                    WHERE run_id = ?
                    ORDER BY sentence_index
                    """,
                    (run_id,),
                ).fetchall()
                immutable_columns = SENTENCE_COLUMNS[:11]
                existing_sentences = [
                    {column: dict(row)[column] for column in immutable_columns}
                    for row in existing_sentence_rows
                ]
                expected_sentences = [
                    {
                        column: self._sentence_value(run_id, sentence, column)
                        for column in immutable_columns
                    }
                    for sentence in sentences
                ]
                if existing_run != expected_run or existing_sentences != expected_sentences:
                    raise ValueError(
                        "동일한 run_id에 다른 payload를 저장할 수 없습니다"
                    )
                self.conn.commit()
                return False

            run_values = tuple(run[column] for column in RUN_COLUMNS)
            self.conn.execute(
                f"INSERT INTO experiment_runs ({', '.join(RUN_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in RUN_COLUMNS)})",
                run_values,
            )
            self.conn.executemany(
                f"INSERT INTO experiment_sentences ({', '.join(SENTENCE_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in SENTENCE_COLUMNS)})",
                [
                    tuple(
                        self._sentence_value(run_id, sentence, column)
                        for column in SENTENCE_COLUMNS
                    )
                    for sentence in sentences
                ],
            )
            self.conn.commit()
            return True
        except BaseException:
            self.conn.rollback()
            raise
    @staticmethod
    def _validate_sentence(sentence: Mapping[str, Any]) -> None:
        disagreement_class = sentence["disagreement_class"]
        if disagreement_class not in DISAGREEMENT_CLASSES:
            raise ValueError(f"unknown disagreement_class: {disagreement_class}")

        hcx_status = sentence["hcx_status"]
        hcx_candidate = sentence["hcx_candidate"]
        if hcx_status == "success":
            if not isinstance(hcx_candidate, bool):
                raise ValueError("successful HCX result requires a boolean candidate")
            expected = classify_disagreement(
                bool(sentence["python_candidate"]),
                hcx_candidate,
                hcx_status,
            )
            if disagreement_class != expected:
                raise ValueError(
                    f"disagreement_class must be {expected} for the stored results"
                )
            return

        if hcx_candidate is not None:
            raise ValueError("failed HCX result must not contain a candidate")
        if disagreement_class != HCX_ERROR:
            raise ValueError("non-success HCX result must use disagreement_class HCX_ERROR")

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

    @staticmethod
    def _run_filters(
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        for expression, value in (
            ("substr(created_at, 1, 10) >= ?", date_from),
            ("substr(created_at, 1, 10) <= ?", date_to),
            ("provider = ?", provider),
            ("model = ?", model),
            ("prompt_version = ?", prompt_version),
        ):
            if value:
                clauses.append(expression)
                values.append(value)
        return (" WHERE " + " AND ".join(clauses) if clauses else "", values)

    def list_runs(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List persisted runs newest first with bounded deterministic pagination."""
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        where, values = self._run_filters(
            date_from=date_from,
            date_to=date_to,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
        )
        rows = self.conn.execute(
            "SELECT * FROM experiment_runs"
            + where
            + " ORDER BY created_at DESC, run_id DESC LIMIT ? OFFSET ?",
            (*values, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_all_runs(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> list[dict[str, Any]]:
        """Collect every filtered run through bounded deterministic pages."""
        result: list[dict[str, Any]] = []
        page_size = 500
        while True:
            page = self.list_runs(
                date_from=date_from,
                date_to=date_to,
                provider=provider,
                model=model,
                prompt_version=prompt_version,
                limit=page_size,
                offset=len(result),
            )
            result.extend(page)
            if len(page) < page_size:
                return result
    def get_sentences_for_runs(
        self, run_ids: Sequence[str]
    ) -> list[dict[str, Any]]:
        """Return sentence-only research rows for selected persisted runs."""
        unique_ids = list(dict.fromkeys(str(run_id) for run_id in run_ids))
        if not unique_ids:
            return []
        placeholders = ", ".join("?" for _ in unique_ids)
        rows = self.conn.execute(
            f"""
            SELECT sentence.*
            FROM experiment_sentences AS sentence
            JOIN experiment_runs AS run ON run.run_id = sentence.run_id
            WHERE sentence.run_id IN ({placeholders})
            ORDER BY run.created_at DESC, run.run_id DESC, sentence.sentence_index
            """,
            unique_ids,
        ).fetchall()
        return [self._sentence_dict(row) for row in rows]

    def get_filtered_sentences(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
        limit_runs: int = 500,
    ) -> list[dict[str, Any]]:
        runs = self.list_runs(
            date_from=date_from,
            date_to=date_to,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            limit=limit_runs,
        )
        return self.get_sentences_for_runs([run["run_id"] for run in runs])
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
