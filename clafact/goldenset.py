"""Research-only Seed 100 goldenset schema and blank template helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping


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


@dataclass(frozen=True)
class SeedManifest:
    """Versioned, research-only contract for one frozen goldenset release."""

    version: str
    target_count: int
    domain_targets: Mapping[str, int]


def blank_seed_rows() -> list[dict[str, str]]:
    """Return the current blank seed rows; the committed template has headers only."""

    with SEED_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def seed_manifest() -> SeedManifest:
    """Load the committed Seed 100 manifest without touching operational data."""

    with SEED_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return SeedManifest(
        version=payload["version"],
        target_count=payload["target_count"],
        domain_targets=payload["domain_targets"],
    )