from dataclasses import FrozenInstanceError

import csv

import pytest

from clafact.goldenset import (
    ALLOWED_REVIEW_STATUSES,
    CLAIM_TYPES,
    CSV_COLUMNS,
    REQUIRED_COLUMNS,
    SEED_CSV_PATH,
    blank_seed_rows,
    seed_manifest,
)


def test_required_columns_preserve_minimum_traceable_claim_contract():
    assert {
        "claim_id",
        "domain",
        "sentence",
        "review_status",
        "kosis_table_id",
    }.issubset(REQUIRED_COLUMNS)


def test_blank_seed_has_no_rows():
    assert blank_seed_rows() == []


def test_seed_manifest_uses_five_balanced_domain_targets():
    manifest = seed_manifest()

    assert manifest.domain_targets == {
        "물가": 20,
        "고용": 20,
        "인구": 20,
        "주거": 20,
        "보건": 20,
    }
    assert manifest.target_count == 100
    with pytest.raises(FrozenInstanceError):
        manifest.version = "v0.2"


def test_seed_constants_keep_controlled_labels_and_stable_csv_order():
    assert ALLOWED_REVIEW_STATUSES == (
        "draft",
        "needs_review",
        "approved",
        "on_hold",
    )
    assert "증감형" in CLAIM_TYPES
    assert CSV_COLUMNS[:5] == (
        "claim_id",
        "domain",
        "sentence",
        "review_status",
        "kosis_table_id",
    )


def test_blank_seed_csv_header_uses_stable_column_order():
    with SEED_CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        assert tuple(next(csv.reader(handle))) == CSV_COLUMNS