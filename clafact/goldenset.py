"""Research-only Seed 100 goldenset schema, loading, and validation helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping, Sequence


GOLDENSET_DIRECTORY: Final[Path] = (
    Path(__file__).resolve().parents[1] / "data" / "research" / "goldenset"
)
SEED_CSV_PATH: Final[Path] = GOLDENSET_DIRECTORY / "seed_v0.1.csv"
SEED_MANIFEST_PATH: Final[Path] = GOLDENSET_DIRECTORY / "seed_manifest_v0.1.json"

DOMAINS: Final[tuple[str, ...]] = ("물가", "고용", "인구", "주거", "보건")
DOMAIN_TARGETS: Final[dict[str, int]] = {
    "물가": 20,
    "고용": 20,
    "인구": 20,
    "주거": 20,
    "보건": 20,
}
ALLOWED_REVIEW_STATUSES: Final[tuple[str, ...]] = (
    "draft",
    "needs_review",
    "approved",
    "on_hold",
)
CLAIM_TYPES: Final[tuple[str, ...]] = (
    "수준형",
    "증감형",
    "비율형",
    "순위형",
    "비교형",
    "추정형",
)
CSV_COLUMNS: Final[tuple[str, ...]] = (
    "claim_id",
    "domain",
    "sentence",
    "review_status",
    "kosis_table_id",
    "article_date",
    "numeric_spans",
    "is_verifiable_claim",
    "claim_type",
    "indicator",
    "value",
    "unit",
    "period",
    "comparison_period",
    "geography",
    "population",
    "kosis_table_title",
    "kosis_selection",
    "kosis_coordinates",
    "official_value",
    "formula",
    "source_url",
    "snapshot_id",
    "annotator",
    "reviewer",
    "review_note",
)
REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "claim_id",
        "domain",
        "sentence",
        "review_status",
        "kosis_table_id",
        "claim_type",
        "indicator",
        "value",
        "unit",
        "period",
        "source_url",
        "annotator",
    }
)
APPROVED_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "indicator",
    "value",
    "unit",
    "period",
    "kosis_table_id",
    "kosis_selection",
    "official_value",
    "source_url",
    "snapshot_id",
    "annotator",
    "reviewer",
)


@dataclass(frozen=True)
class SeedManifest:
    """Versioned, research-only contract for one frozen goldenset release."""

    version: str
    target_count: int
    domain_targets: Mapping[str, int]


@dataclass(frozen=True)
class ValidationIssue:
    """One non-mutating validation finding for a goldenset record."""

    code: str
    severity: str
    claim_id: str
    field: str
    message: str


def blank_seed_rows() -> list[dict[str, str]]:
    """Return the current blank seed rows; the committed template has headers only."""

    return load_csv(SEED_CSV_PATH)


def seed_manifest() -> SeedManifest:
    """Load the committed Seed 100 manifest without touching operational data."""

    with SEED_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return SeedManifest(
        version=payload["version"],
        target_count=payload["target_count"],
        domain_targets=payload["domain_targets"],
    )


def load_csv(path: str | Path) -> list[dict[str, str]]:
    """Load a goldenset CSV without altering source values."""

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_jsonl(path: str | Path) -> list[dict[str, object]]:
    """Load non-empty JSONL records without altering source values."""

    rows: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL row {line_number} must be an object")
            rows.append(payload)
    return rows


def validate_rows(rows: Sequence[Mapping[str, object]]) -> list[ValidationIssue]:
    """Return validation issues for rows without modifying their source mappings."""

    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    seen_sentences: set[str] = set()

    for row in rows:
        claim_id = _text(row.get("claim_id"))
        sentence = _text(row.get("sentence"))

        for field in sorted(REQUIRED_COLUMNS):
            if not _text(row.get(field)):
                issues.append(
                    _issue(
                        "required_field",
                        claim_id,
                        field,
                        f"{field} is required",
                    )
                )

        domain = _text(row.get("domain"))
        if domain and domain not in DOMAINS:
            issues.append(_issue("invalid_domain", claim_id, "domain", "domain is not allowed"))

        review_status = _text(row.get("review_status"))
        if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
            issues.append(
                _issue(
                    "invalid_review_status",
                    claim_id,
                    "review_status",
                    "review_status is not allowed",
                )
            )

        claim_type = _text(row.get("claim_type"))
        if claim_type and claim_type not in CLAIM_TYPES:
            issues.append(
                _issue(
                    "invalid_claim_type",
                    claim_id,
                    "claim_type",
                    "claim_type is not allowed",
                )
            )

        if claim_id:
            if claim_id in seen_ids:
                issues.append(
                    _issue(
                        "duplicate_claim_id",
                        claim_id,
                        "claim_id",
                        "claim_id must be distinct",
                    )
                )
            seen_ids.add(claim_id)

        normalized_sentence = _normalize_sentence(sentence)
        if normalized_sentence:
            if normalized_sentence in seen_sentences:
                issues.append(
                    _issue(
                        "duplicate_sentence",
                        claim_id,
                        "sentence",
                        "sentence duplicates another row after normalization",
                    )
                )
            seen_sentences.add(normalized_sentence)

        if review_status == "approved":
            for field in APPROVED_REQUIRED_FIELDS:
                if not _text(row.get(field)):
                    issues.append(
                        _issue(
                            "approved_kosis_required",
                            claim_id,
                            field,
                            f"approved rows require {field}",
                        )
                    )

    return issues


def validate_semantic_parity(
    csv_rows: Sequence[Mapping[str, object]],
    jsonl_rows: Sequence[Mapping[str, object]],
) -> list[ValidationIssue]:
    """Report differing IDs or field values between CSV and JSONL representations."""

    csv_by_id = _rows_by_claim_id(csv_rows)
    jsonl_by_id = _rows_by_claim_id(jsonl_rows)
    issues: list[ValidationIssue] = []

    for claim_id in sorted(csv_by_id.keys() - jsonl_by_id.keys()):
        issues.append(
            _issue(
                "parity_missing_in_jsonl",
                claim_id,
                "claim_id",
                "claim_id exists in CSV but not JSONL",
            )
        )
    for claim_id in sorted(jsonl_by_id.keys() - csv_by_id.keys()):
        issues.append(
            _issue(
                "parity_missing_in_csv",
                claim_id,
                "claim_id",
                "claim_id exists in JSONL but not CSV",
            )
        )

    for claim_id in sorted(csv_by_id.keys() & jsonl_by_id.keys()):
        csv_row = csv_by_id[claim_id]
        jsonl_row = jsonl_by_id[claim_id]
        for field in sorted(set(csv_row) | set(jsonl_row)):
            if _text(csv_row.get(field)) != _text(jsonl_row.get(field)):
                issues.append(
                    _issue(
                        "parity_field_mismatch",
                        claim_id,
                        field,
                        "field values differ between CSV and JSONL",
                    )
                )

    return issues


def _rows_by_claim_id(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, Mapping[str, object]]:
    return {
        claim_id: row
        for row in rows
        if (claim_id := _text(row.get("claim_id")))
    }


def _normalize_sentence(value: str) -> str:
    return " ".join(value.split()).casefold()


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _issue(code: str, claim_id: str, field: str, message: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity="error",
        claim_id=claim_id,
        field=field,
        message=message,
    )
