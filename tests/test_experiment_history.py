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
