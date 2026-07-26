"""Export and human-approved golden promotion for research-only lab runs."""
from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from clafact.experiment_store import ExperimentStore, RUN_COLUMNS, SENTENCE_COLUMNS


CSV_COLUMNS = (*RUN_COLUMNS, *(column for column in SENTENCE_COLUMNS if column != "run_id"))
PROMOTABLE_LABELS = frozenset({"true_candidate", "false_positive"})
PROMOTABLE_DISAGREEMENTS = frozenset({"P+/H-", "P-/H+"})
_SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_LOCK_RETRIES = 200
_LOCK_RETRY_SECONDS = 0.01


def _spreadsheet_safe(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(_SPREADSHEET_FORMULA_PREFIXES):
        return "'" + value
    return value


def export_run_csv(store: ExperimentStore, run_id: str) -> bytes:
    """Return one persisted run as deterministic Excel-safe UTF-8 BOM CSV bytes."""
    run = store.get_run(run_id)
    if run is None:
        raise KeyError(f"실험 실행을 찾을 수 없습니다: {run_id}")

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for sentence in store.get_sentences(run_id):
        combined = {**run, **sentence}
        writer.writerow({column: _spreadsheet_safe(combined.get(column)) for column in CSV_COLUMNS})
    return output.getvalue().encode("utf-8-sig")


def _sentence_for_promotion(
    store: ExperimentStore,
    run_id: str,
    sentence_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    run = store.get_run(run_id)
    if run is None:
        raise KeyError(f"실험 실행을 찾을 수 없습니다: {run_id}")
    sentence = next(
        (row for row in store.get_sentences(run_id) if row["sentence_index"] == sentence_index),
        None,
    )
    if sentence is None:
        raise KeyError((run_id, sentence_index))
    if sentence["human_label"] not in PROMOTABLE_LABELS:
        raise ValueError("true_candidate 또는 false_positive 검토 완료 문장만 승격할 수 있습니다")
    if sentence["disagreement_class"] not in PROMOTABLE_DISAGREEMENTS:
        raise ValueError("P+/H- 또는 P-/H+ 불일치 문장만 골든셋에 승격할 수 있습니다")
    return run, sentence


@contextmanager
def _exclusive_file_lock(target: Path) -> Iterator[None]:
    """Acquire an adjacent cross-process lock with a bounded wait."""
    lock_path = target.with_name(target.name + ".lock")
    descriptor: int | None = None
    for attempt in range(_LOCK_RETRIES):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if attempt == _LOCK_RETRIES - 1:
                raise TimeoutError(f"골든셋 잠금을 획득하지 못했습니다: {lock_path}")
            time.sleep(_LOCK_RETRY_SECONDS)

    assert descriptor is not None
    try:
        try:
            os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _read_existing_jsonl(path: Path, sentence_hash: str) -> str:
    if not path.exists():
        return ""
    existing_text = path.read_text(encoding="utf-8")
    for line in existing_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("sentence_hash") == sentence_hash:
            raise ValueError("이미 골든셋에 등록된 문장입니다")
    return existing_text


def _atomic_append_jsonl(path: Path, existing_text: str, row: dict[str, Any]) -> None:
    prefix = existing_text
    if prefix and not prefix.endswith(("\n", "\r")):
        prefix += "\n"
    complete_text = prefix + json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(complete_text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def promote_to_golden(
    store: ExperimentStore,
    run_id: str,
    sentence_index: int,
    golden_path: str | Path,
) -> dict[str, Any]:
    """Atomically append one explicitly selected, human-reviewed disagreement."""
    run, sentence = _sentence_for_promotion(store, run_id, sentence_index)
    golden_row = {
        "sentence_hash": sentence["sentence_hash"],
        "sentence_text": sentence["sentence_text"],
        "disagreement_class": sentence["disagreement_class"],
        "human_label": sentence["human_label"],
        "python_reason": sentence["python_reason"],
        "hcx_reason": sentence["hcx_reason"],
        "evidence_status": sentence["evidence_status"],
        "provider": run["provider"],
        "model": run["model"],
        "prompt_version": run["prompt_version"],
        "reviewed_at": sentence["reviewed_at"],
        "source_run_id": run_id,
        "source_sentence_index": sentence_index,
    }
    path = Path(golden_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_file_lock(path):
        existing_text = _read_existing_jsonl(path, sentence["sentence_hash"])
        _atomic_append_jsonl(path, existing_text, golden_row)
    return golden_row
