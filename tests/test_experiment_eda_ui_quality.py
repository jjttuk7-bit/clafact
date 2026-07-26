from pathlib import Path


def _lab_section() -> str:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    return source[
        source.index('if view == "검증 실험실":'):
        source.index("# ═════════════ 탭 2: 검증자 리뷰")
    ]


def test_upload_gate_uses_streaming_metadata_and_reads_only_confirmed_large_range():
    section = _lab_section()
    upload = section[
        section.index("selected_lab_article = None"):
        section.index("lab_date =")
    ]

    assert "lab_csv.getvalue()" not in upload
    assert "list(csv.DictReader" not in upload
    assert "UploadIdentity(" in upload
    assert "cached_upload_metadata(" in upload
    assert "hash_seekable_stream(" in upload
    assert "scan_csv_stream(" in upload
    assert "store_upload_metadata(" in upload
    assert "read_csv_range(lab_csv, selected_eda_range)" in upload
    assert upload.index("if range_submitted:") < upload.index(
        "read_csv_range(lab_csv, selected_eda_range)"
    )
    assert "scan.rows" in upload


def test_cache_scope_is_prepared_before_filter_widgets_are_rendered():
    section = _lab_section()
    eda = section[
        section.index("current_cache_key ="):
        section.index("lab_date =")
    ]

    assert "prepare_cache_scope(st.session_state, current_cache_key)" in eda
    assert eda.index("prepare_cache_scope(") < eda.index(
        'with st.form("experiment_eda_article_filters")'
    )


def test_current_comparison_signature_invalidates_stale_results_before_rendering():
    section = _lab_section()

    assert "comparison_input_signature(" in section
    assert "invalidate_comparison_for_input(" in section
    assert "source_row=selected_lab_article" in section
    assert "file_signature=lab_signature" in section
    assert section.index("invalidate_comparison_for_input(") < section.index(
        'result = st.session_state.get("experiment_lab_result")'
    )
