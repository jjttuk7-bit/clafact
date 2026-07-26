from __future__ import annotations

import io

import pytest

from clafact.experiment_eda_session import (
    COMPARISON_INPUT_SIGNATURE_KEY,
    MAX_EDA_CSV_FIELD_CHARS,
    EdaCsvReadError,
    EDA_CACHE_KEY,
    EDA_FILTER_STATE_KEYS,
    EDA_REPORT_KEY,
    EDA_SELECTED_ARTICLE_KEY,
    EDA_UPLOAD_METADATA_KEY,
    EDA_VIEW_KEY,
    EdaRange,
    UploadIdentity,
    UploadMetadata,
    cached_upload_metadata,
    comparison_input_signature,
    hash_seekable_stream,
    invalidate_comparison_for_input,
    prepare_cache_scope,
    read_csv_range,
    scan_csv_stream,
    store_upload_metadata,
)


def _csv_payload(row_count: int) -> bytes:
    lines = ["title,date,body"]
    lines.extend(
        f"article-{number},2025-01-01,{number}% rose"
        for number in range(1, row_count + 1)
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_hash_stream_reads_in_chunks_and_restores_the_callers_position():
    stream = io.BytesIO(_csv_payload(3))
    stream.seek(7)

    first = hash_seekable_stream(stream, chunk_size=5)
    second = hash_seekable_stream(stream, chunk_size=11)

    assert first == second
    assert stream.tell() == 7


def test_large_initial_scan_counts_all_rows_without_returning_the_full_list():
    stream = io.BytesIO(_csv_payload(1_501))
    stream.seek(4)

    scan = scan_csv_stream(stream)

    assert scan.row_count == 1_501
    assert scan.rows == ()
    assert scan.retained_during_scan == 1_001
    assert scan.exceeded_limit is True
    assert stream.tell() == 4


def test_small_initial_scan_retains_rows_for_same_run_analysis():
    scan = scan_csv_stream(io.BytesIO(_csv_payload(3)))

    assert scan.row_count == 3
    assert [row["title"] for row in scan.rows] == [
        "article-1",
        "article-2",
        "article-3",
    ]
    assert scan.exceeded_limit is False


def test_confirmed_range_is_read_inclusively_without_off_by_one():
    stream = io.BytesIO(_csv_payload(1_500))
    stream.seek(9)

    rows = read_csv_range(stream, EdaRange(501, 1_500))

    assert len(rows) == 1_000
    assert rows[0]["title"] == "article-501"
    assert rows[-1]["title"] == "article-1500"
    assert stream.tell() == 9


@pytest.mark.parametrize("operation", [scan_csv_stream, lambda stream: read_csv_range(stream, EdaRange(1, 1))])
def test_streaming_csv_operations_restore_position_on_invalid_utf8(operation):
    stream = io.BytesIO(b"title,body\nbad,\xff\n")
    stream.seek(2)

    with pytest.raises(UnicodeDecodeError):
        operation(stream)

    assert stream.tell() == 2


def test_same_upload_identity_reuses_metadata_without_storing_payload_rows():
    identity = UploadIdentity(file_id="file-1", name="news.csv", size=123)
    metadata = UploadMetadata(identity, signature="abc", row_count=2)
    state = {}

    assert store_upload_metadata(state, metadata) is True
    assert cached_upload_metadata(state, identity) == metadata
    assert store_upload_metadata(state, metadata) is False
    assert state == {EDA_UPLOAD_METADATA_KEY: metadata}


def test_new_upload_identity_invalidates_old_eda_state():
    old = UploadMetadata(
        UploadIdentity("old", "same.csv", 123),
        signature="same-content",
        row_count=2,
    )
    new = UploadMetadata(
        UploadIdentity("new", "same.csv", 123),
        signature="same-content",
        row_count=2,
    )
    state = {
        EDA_UPLOAD_METADATA_KEY: old,
        EDA_CACHE_KEY: ("old", 1, 2),
        EDA_REPORT_KEY: object(),
        EDA_VIEW_KEY: object(),
        EDA_SELECTED_ARTICLE_KEY: 2,
    }

    assert cached_upload_metadata(state, new.identity) is None
    assert store_upload_metadata(state, new) is True
    assert state == {EDA_UPLOAD_METADATA_KEY: new}


def test_new_cache_range_resets_filter_and_selected_article_before_widgets():
    state = {
        EDA_CACHE_KEY: ("file", 1, 1000),
        EDA_REPORT_KEY: object(),
        EDA_VIEW_KEY: object(),
        EDA_SELECTED_ARTICLE_KEY: 999,
        EDA_FILTER_STATE_KEYS[0]: "warnings",
        EDA_FILTER_STATE_KEYS[2]: 8,
        EDA_FILTER_STATE_KEYS[3]: 12,
    }

    assert prepare_cache_scope(state, ("file", 1001, 2000)) is True
    assert state == {EDA_CACHE_KEY: ("file", 1001, 2000)}
    assert prepare_cache_scope(state, ("file", 1001, 2000)) is False


def test_comparison_signature_covers_every_effective_input_dimension():
    baseline = comparison_input_signature(
        text="exact text",
        article_date="2025-01-01",
        title="title",
        source_row=7,
        file_signature="file-a",
        upload_identity=UploadIdentity("upload-a", "news.csv", 10),
        analysis_range=EdaRange(1, 10),
    )
    variants = (
        {"text": "exact text "},
        {"article_date": "2025-01-02"},
        {"title": "other"},
        {"source_row": 8},
        {"file_signature": "file-b"},
        {"upload_identity": UploadIdentity("upload-b", "news.csv", 10)},
        {"analysis_range": EdaRange(2, 10)},
    )
    for change in variants:
        values = {
            "text": "exact text",
            "article_date": "2025-01-01",
            "title": "title",
            "source_row": 7,
            "file_signature": "file-a",
            "upload_identity": UploadIdentity("upload-a", "news.csv", 10),
            "analysis_range": EdaRange(1, 10),
            **change,
        }
        assert comparison_input_signature(**values) != baseline


def test_changed_comparison_input_clears_only_stale_execution_state():
    state = {
        COMPARISON_INPUT_SIGNATURE_KEY: "old",
        "experiment_lab_result": object(),
        "experiment_lab_mode_result": object(),
        "experiment_lab_run_context": object(),
        "experiment_lab_saved_run_id": "run",
        "unrelated": "keep",
    }

    assert invalidate_comparison_for_input(state, "new") is True
    assert state == {
        COMPARISON_INPUT_SIGNATURE_KEY: "new",
        "unrelated": "keep",
    }


def test_unchanged_comparison_input_preserves_completed_execution():
    result = object()
    state = {
        COMPARISON_INPUT_SIGNATURE_KEY: "same",
        "experiment_lab_result": result,
        "experiment_lab_saved_run_id": "run",
    }

    assert invalidate_comparison_for_input(state, "same") is False
    assert state["experiment_lab_result"] is result
    assert state["experiment_lab_saved_run_id"] == "run"


def test_csv_body_above_legacy_128k_limit_scans_and_reads_without_crash():
    body = "가" * 131_073
    payload = f'title,date,body\n큰 기사,2025-11-04,"{body}"\n'.encode("utf-8")
    stream = io.BytesIO(payload)
    stream.seek(11)

    scan = scan_csv_stream(stream)
    ranged = read_csv_range(io.BytesIO(payload), EdaRange(1, 1))

    assert scan.row_count == 1
    assert len(scan.rows[0]["body"]) == 131_073
    assert len(ranged[0]["body"]) == 131_073
    assert stream.tell() == 11


def test_csv_field_above_documented_limit_is_explicit_and_restores_position():
    body = "x" * (MAX_EDA_CSV_FIELD_CHARS + 1)
    stream = io.BytesIO(f"title,body\n초과,{body}\n".encode("utf-8"))
    stream.seek(5)

    with pytest.raises(EdaCsvReadError) as captured:
        scan_csv_stream(stream)

    assert f"{MAX_EDA_CSV_FIELD_CHARS:,}자" in captured.value.user_message
    assert "줄이지 않고" in captured.value.user_message
    assert stream.tell() == 5


def test_malformed_csv_is_a_typed_user_safe_error_and_restores_position():
    stream = io.BytesIO(b'title,body\nbad,"unterminated\n')
    stream.seek(3)

    with pytest.raises(EdaCsvReadError) as captured:
        read_csv_range(stream, EdaRange(1, 1))

    assert captured.value.user_message == (
        "CSV 형식을 읽을 수 없습니다. 따옴표와 열 구분자를 확인해 주세요."
    )
    assert stream.tell() == 3
