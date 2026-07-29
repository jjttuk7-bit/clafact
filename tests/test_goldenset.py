from dataclasses import FrozenInstanceError
import csv
import io
import json

import pytest

from clafact.goldenset import (
    ALLOWED_REVIEW_STATUSES,
    CLAIM_TYPES,
    CSV_COLUMNS,
    REQUIRED_COLUMNS,
    SEED_CSV_PATH,
    ValidationIssue,
    blank_seed_rows,
    load_csv,
    load_jsonl,
    seed_manifest,
    summarize_rows,
    validate_rows,
    validate_semantic_parity,
    validation_report_csv,
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


def valid_row(**overrides):
    row = {column: "example" for column in CSV_COLUMNS}
    row.update(
        {
            "claim_id": "seed-001",
            "domain": "물가",
            "sentence": "소비자물가가 2.4% 상승했다.",
            "review_status": "approved",
            "kosis_table_id": "DT_1J22042",
            "claim_type": "증감형",
            "indicator": "전년동월비(%)",
            "value": "2.4",
            "unit": "%",
            "period": "2025-10",
            "kosis_selection": "지수종류=총지수",
            "official_value": "2.4",
            "source_url": "https://kosis.kr/example",
            "snapshot_id": "snapshot-001",
            "annotator": "researcher-a",
            "reviewer": "reviewer-b",
        }
    )
    row.update(overrides)
    return row


def test_validate_rows_reports_blank_kosis_or_official_answer_for_approved_row():
    issues = validate_rows(
        [
            valid_row(
                kosis_table_id="",
                kosis_selection="",
                official_value="",
                source_url="",
                snapshot_id="",
            )
        ]
    )

    assert any(issue.code == "approved_kosis_required" for issue in issues)


def test_validate_rows_reports_duplicate_id_and_normalized_duplicate_sentence():
    issues = validate_rows(
        [
            valid_row(),
            valid_row(
                sentence="  소비자물가가   2.4% 상승했다. ",
                reviewer="reviewer-c",
            ),
        ]
    )

    assert {issue.code for issue in issues} >= {
        "duplicate_claim_id",
        "duplicate_sentence",
    }


def test_validation_issue_is_an_immutable_data_record():
    issue = ValidationIssue(
        code="required",
        severity="error",
        claim_id="seed-001",
        field="sentence",
        message="sentence is required",
    )

    assert issue.claim_id == "seed-001"
    with pytest.raises(FrozenInstanceError):
        issue.code = "changed"


def test_loaders_and_semantic_parity_report_id_and_field_differences(tmp_path):
    csv_path = tmp_path / "seed.csv"
    jsonl_path = tmp_path / "seed.jsonl"
    csv_row = valid_row()
    jsonl_row = valid_row(claim_id="seed-002", unit="명")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(csv_row)
    jsonl_path.write_text(json.dumps(jsonl_row, ensure_ascii=False) + "\n", encoding="utf-8")

    assert load_csv(csv_path) == [csv_row]
    assert load_jsonl(jsonl_path) == [jsonl_row]

    issues = validate_semantic_parity(load_csv(csv_path), load_jsonl(jsonl_path))

    assert {issue.code for issue in issues} >= {
        "parity_missing_in_csv",
        "parity_missing_in_jsonl",
    }


def test_semantic_parity_reports_duplicate_ids_on_each_side_without_losing_rows():
    csv_rows = [valid_row(), valid_row(reviewer="reviewer-c")]
    jsonl_rows = [valid_row(), valid_row(reviewer="reviewer-c")]

    issues = validate_semantic_parity(csv_rows, jsonl_rows)

    duplicate_issues = [
        issue
        for issue in issues
        if issue.code == "parity_duplicate_claim_id" and issue.claim_id == "seed-001"
    ]
    assert len(duplicate_issues) == 2
    assert all("claim_id" in issue.message for issue in duplicate_issues)


def test_semantic_parity_reports_claim_id_multiplicity_mismatch():
    issues = validate_semantic_parity(
        [valid_row(), valid_row(reviewer="reviewer-c")],
        [valid_row()],
    )

    assert any(
        issue.code == "parity_claim_id_multiplicity_mismatch"
        and issue.claim_id == "seed-001"
        for issue in issues
    )


def test_summary_reports_domain_gap_review_counts_and_csv_issue_header():
    summary = summarize_rows(
        [
            valid_row(claim_id="seed-001", domain="물가", review_status="approved"),
            valid_row(
                claim_id="seed-002",
                domain="고용",
                review_status="needs_review",
                reviewer="",
            ),
        ]
    )

    assert summary.target_count == 100
    assert summary.current_count == 2
    assert summary.domain_counts["물가"].current == 1
    assert summary.domain_counts["물가"].gap == 19
    assert summary.review_counts["approved"] == 1
    assert summary.valid_evaluation_count == 1
    payload = validation_report_csv(summary.issues)
    assert payload.startswith(b"\xef\xbb\xbf")
    assert "issue_code" in payload.decode("utf-8-sig")


def test_validation_report_uses_korean_validation_messages():
    issues = validate_rows([valid_row(domain="")])

    report_rows = list(
        csv.DictReader(io.StringIO(validation_report_csv(issues).decode("utf-8-sig")))
    )

    assert any(row["message"] == "domain은(는) 필수입니다." for row in report_rows)
