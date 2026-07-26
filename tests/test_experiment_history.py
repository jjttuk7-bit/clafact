from clafact.experiment_history import (
    DISAGREEMENT_ORDER,
    build_history_summary,
    distinct_filter_values,
)


def test_cumulative_summary_counts_all_five_types_without_accuracy_claims():
    runs = [
        {"run_id": "run-a", "provider": "HCX", "model": "HCX-005", "prompt_version": "v2"},
        {"run_id": "run-b", "provider": "GPT", "model": "gpt-5", "prompt_version": "v3"},
    ]
    sentences = [
        {"run_id": "run-a", "disagreement_class": "P+/H+"},
        {"run_id": "run-a", "disagreement_class": "P+/H-"},
        {"run_id": "run-b", "disagreement_class": "P-/H+"},
        {"run_id": "run-b", "disagreement_class": "P-/H-"},
        {"run_id": "run-b", "disagreement_class": "HCX_ERROR"},
    ]

    summary = build_history_summary(runs, sentences)

    assert summary.run_count == 2
    assert summary.sentence_count == 5
    assert tuple(summary.counts) == DISAGREEMENT_ORDER
    assert summary.counts == {
        "P+/H+": 1, "P+/H-": 1, "P-/H+": 1, "P-/H-": 1, "HCX_ERROR": 1
    }
    assert not hasattr(summary, "precision")
    assert not hasattr(summary, "recall")


def test_distinct_history_filters_are_sorted_and_ignore_blanks():
    runs = [
        {"provider": "HCX", "model": "HCX-005", "prompt_version": "v2"},
        {"provider": "GPT", "model": "gpt-5", "prompt_version": "v3"},
        {"provider": "HCX", "model": "", "prompt_version": "v2"},
    ]
    assert distinct_filter_values(runs, "provider") == ("GPT", "HCX")
    assert distinct_filter_values(runs, "model") == ("HCX-005", "gpt-5")


def test_history_filter_signature_invalidates_prepared_export_and_pages_are_bounded():
    from clafact.experiment_history import (
        HistoryFilters,
        PreparedHistoryExport,
        build_history_page,
        filter_signature,
        prepared_export_for_filters,
    )

    filters = HistoryFilters("2026-07-01", "2026-07-26", "HCX", "HCX-005", "v2")
    signature = filter_signature(filters)
    prepared = PreparedHistoryExport(signature=signature, payload=b"csv", row_count=4)

    assert prepared_export_for_filters(prepared, filters) == prepared
    assert prepared_export_for_filters(
        prepared,
        HistoryFilters("2026-07-01", "2026-07-26", "GPT", "gpt-5", "v2"),
    ) is None
    assert build_history_page(total_runs=501, requested_page=99, page_size=50) == {
        "page": 11, "page_count": 11, "offset": 500
    }
    assert build_history_page(total_runs=0, requested_page=3, page_size=50) == {
        "page": 1, "page_count": 1, "offset": 0
    }


def test_history_action_target_preserves_selected_past_run_and_sentence():
    from clafact.experiment_history import build_history_action_target

    target = build_history_action_target("past-run-42", 7)
    assert target.run_id == "past-run-42"
    assert target.sentence_index == 7


def test_huge_history_page_has_constant_size_metadata():
    from clafact.experiment_history import build_history_page

    page = build_history_page(total_runs=10_000_000, requested_page=3, page_size=50)
    assert page == {"page": 3, "page_count": 200_000, "offset": 100}
    assert "options" not in page
