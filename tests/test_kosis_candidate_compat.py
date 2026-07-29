from clafact.kosis_candidate_compat import search_candidates_with_context


def test_retries_without_context_for_stale_candidate_search_signature():
    calls = []

    def stale_search(sentence, index, *, metadata_client=None):
        calls.append((sentence, index, metadata_client))
        return ["candidate"]

    result = search_candidates_with_context(
        stale_search,
        "이같은 물가 상승률은 높다.",
        "index",
        metadata_client="metadata",
        previous_profile="previous",
    )

    assert result == ["candidate"]
    assert calls == [("이같은 물가 상승률은 높다.", "index", "metadata")]
