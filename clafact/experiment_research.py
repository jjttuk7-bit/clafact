"""Research-only persistence helpers for verification-lab comparisons."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from clafact.experiment_store import ExperimentStore


@dataclass(frozen=True)
class ExperimentRunContext:
    run_id: str
    created_at: str
    input_fingerprint: str
    article_hash: str
    article_text: str
    article_title: str
    article_date: str
    source_row_count: int
    provider: str
    model: str
    prompt_version: str


@dataclass(frozen=True)
class SaveOutcome:
    run_id: str
    created: bool


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def comparison_input_fingerprint(article_text: str, article_date: str) -> str:
    payload = json.dumps(
        {"article_date": article_date, "article_text": article_text},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(payload)


def build_run_context(
    *,
    article_text: str,
    article_date: str,
    article_title: str,
    source_row_count: int,
    prompt_version: str,
    provider: str = "HCX",
    model: str = "HCX-005",
    created_at: str | None = None,
    run_token: str | None = None,
) -> ExperimentRunContext:
    fingerprint = comparison_input_fingerprint(article_text, article_date)
    timestamp = created_at or datetime.now().astimezone().isoformat(timespec="milliseconds")
    token = run_token or uuid4().hex[:10]
    return ExperimentRunContext(
        run_id=f"vlab-{fingerprint[:16]}-{token}",
        created_at=timestamp,
        input_fingerprint=fingerprint,
        article_hash=_sha256_text(article_text),
        article_text=article_text,
        article_title=article_title,
        article_date=article_date,
        source_row_count=source_row_count,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
    )


def input_matches_context(
    article_text: str,
    article_date: str,
    context: ExperimentRunContext,
) -> bool:
    return comparison_input_fingerprint(article_text, article_date) == context.input_fingerprint


def semantic_disagreement_count(result: Any) -> int:
    semantic_classes = {"P+/H-", "P-/H+"}
    return sum(row.disagreement_class in semantic_classes for row in result.rows)


def save_comparison_run(
    database_path: str | Path,
    result: Any,
    context: ExperimentRunContext,
) -> SaveOutcome:
    """Idempotently persist one explicitly requested full-comparison execution."""
    mode_results = getattr(result, "mode_results", {})
    if not {"python", "llm", "hybrid"}.issubset(mode_results):
        raise ValueError("전체 비교 결과만 연구 이력에 저장할 수 있습니다")

    python_result = mode_results["python"]
    hcx_result = mode_results["llm"]
    run_row = {
        "run_id": context.run_id,
        "created_at": context.created_at,
        "article_hash": context.article_hash,
        "article_title": context.article_title,
        "article_date": context.article_date,
        "provider": context.provider,
        "model": context.model,
        "prompt_version": context.prompt_version,
        "python_ms": python_result.elapsed_ms,
        "hcx_ms": hcx_result.elapsed_ms,
        "total_ms": result.elapsed_ms,
        "hcx_calls": result.llm_calls,
        "source_row_count": context.source_row_count,
        "sentence_count": len(result.rows),
    }
    sentence_rows = []
    for sentence_index, (row, python_row) in enumerate(
        zip(result.rows, python_result.rows), start=1
    ):
        hcx_candidate = row.llm_verifiable if row.hcx_status == "success" else None
        sentence_rows.append({
            "sentence_index": sentence_index,
            "sentence_hash": _sha256_text(row.sentence),
            "sentence_text": row.sentence,
            "python_candidate": row.python_candidate,
            "python_reason": python_row.reason,
            "hcx_status": row.hcx_status,
            "hcx_candidate": hcx_candidate,
            "hcx_reason": row.llm_reason,
            "evidence_status": row.hcx_evidence_status,
            "disagreement_class": row.disagreement_class,
        })

    with ExperimentStore(database_path) as research_store:
        created = research_store.append_run_idempotent(run_row, sentence_rows)
    return SaveOutcome(context.run_id, created=created)
