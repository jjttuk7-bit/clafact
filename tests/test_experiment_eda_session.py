import pytest

from clafact.experiment_eda_session import (
    EDA_CACHE_KEY,
    EDA_FILE_SIGNATURE_KEY,
    EDA_FILTER_STATE_KEYS,
    EDA_REPORT_KEY,
    EDA_SELECTED_ARTICLE_KEY,
    EDA_VIEW_KEY,
    MAX_EDA_ROWS,
    EdaRange,
    analysis_scope_caption,
    cache_key,
    invalidate_for_payload,
    payload_signature,
    resolve_eda_range,
)


def test_payload_signature_is_stable_and_does_not_require_storing_bytes():
    payload = b"title,body\nA,1% rose"

    assert payload_signature(payload) == payload_signature(bytes(payload))
    assert payload_signature(payload) != payload_signature(payload + b"\n")


def test_small_upload_resolves_to_the_full_one_based_source_range():
    selected = resolve_eda_range(total_rows=17)

    assert selected == EdaRange(start=1, end=17)
    assert selected.slice_bounds == (0, 17)
    assert selected.span == 17


def test_large_upload_requires_an_explicit_confirmed_bounded_range():
    assert resolve_eda_range(total_rows=1001) is None
    assert (
        resolve_eda_range(
            total_rows=1001,
            requested=EdaRange(2, 1001),
            confirmed=False,
        )
        is None
    )
    assert resolve_eda_range(
        total_rows=1001,
        requested=EdaRange(2, 1001),
        confirmed=True,
    ) == EdaRange(2, 1001)


@pytest.mark.parametrize(
    "selected",
    [
        EdaRange(1, MAX_EDA_ROWS + 1),
        EdaRange(0, 1),
        EdaRange(3, 2),
        EdaRange(1, 10_001),
    ],
)
def test_range_rejects_invalid_bounds_or_more_than_one_thousand_rows(selected):
    with pytest.raises(ValueError):
        resolve_eda_range(
            total_rows=10_000,
            requested=selected,
            confirmed=True,
        )


def test_cache_key_includes_file_identity_and_exact_range():
    selected = EdaRange(1001, 2000)

    assert cache_key("abc", selected) == ("abc", 1001, 2000)
    assert cache_key("def", selected) != cache_key("abc", selected)


def test_new_file_signature_clears_report_view_selection_filters_and_cache():
    state = {
        EDA_FILE_SIGNATURE_KEY: "old",
        EDA_REPORT_KEY: object(),
        EDA_VIEW_KEY: object(),
        EDA_CACHE_KEY: ("old", 1, 2),
        EDA_SELECTED_ARTICLE_KEY: 2,
        **{key: "stale" for key in EDA_FILTER_STATE_KEYS},
        "unrelated": "keep",
    }

    changed = invalidate_for_payload(state, "new")

    assert changed is True
    assert state[EDA_FILE_SIGNATURE_KEY] == "new"
    assert state["unrelated"] == "keep"
    assert EDA_REPORT_KEY not in state
    assert EDA_VIEW_KEY not in state
    assert EDA_CACHE_KEY not in state
    assert EDA_SELECTED_ARTICLE_KEY not in state
    assert all(key not in state for key in EDA_FILTER_STATE_KEYS)
    assert all(not isinstance(value, bytes) for value in state.values())


def test_same_file_signature_preserves_existing_eda_state():
    report = object()
    state = {
        EDA_FILE_SIGNATURE_KEY: "same",
        EDA_REPORT_KEY: report,
        EDA_SELECTED_ARTICLE_KEY: 3,
    }

    assert invalidate_for_payload(state, "same") is False
    assert state[EDA_REPORT_KEY] is report
    assert state[EDA_SELECTED_ARTICLE_KEY] == 3


def test_small_upload_scope_caption_is_truthful_about_the_full_population():
    assert analysis_scope_caption(17, EdaRange(1, 17)) == "전체 17행 중 1–17행 분석"
