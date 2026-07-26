"""Export and human-approved golden promotion for research-only lab runs."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from clafact.experiment_store import ExperimentStore, RUN_COLUMNS, SENTENCE_COLUMNS


CSV_COLUMNS = (*RUN_COLUMNS, *(column for column in SENTENCE_COLUMNS if column != "run_id"))
PROMOTABLE_LABELS = frozenset({"true_candidate", "false_positive"})
_SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


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
    return run, sentence


def promote_to_golden(
    store: ExperimentStore,
    run_id: str,
    sentence_index: int,
    golden_path: str | Path,
) -> dict[str, Any]:
    """Append one explicitly selected, human-reviewed sentence without overwriting."""
    run, sentence = _sentence_for_promotion(store, run_id, sentence_index)
    path = Path(golden_path)
    if path.exists():
        with path.open("r", encoding="utf-8") as existing:
            for line in existing:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("sentence_hash") == sentence["sentence_hash"]:
                    raise ValueError("이미 골든셋에 등록된 문장입니다")

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
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_separator = path.exists() and path.stat().st_size > 0
    if needs_separator:
        with path.open("rb") as existing_bytes:
            existing_bytes.seek(-1, 2)
            needs_separator = existing_bytes.read(1) != b"\n"
    with path.open("a", encoding="utf-8", newline="\n") as output:
        if needs_separator:
            output.write("\n")
        output.write(json.dumps(golden_row, ensure_ascii=False, sort_keys=True) + "\n")
    return golden_row
