from clafact.claim_context import resolve_article_period, shadow_sentence_label


def test_unique_strong_article_period_is_available_to_later_sentence():
    context = resolve_article_period(
        ["지난달 소비자물가가 2.4% 올랐다.", "배추는 -34.5%다."],
        "2025-11-04",
    )

    assert context.period == "2025-10"
    assert context.row_index == 1


def test_conflicting_strong_periods_do_not_auto_inherit():
    context = resolve_article_period(
        ["지난달 소비자물가가 올랐다.", "2025년 8월 소비자물가가 올랐다."],
        "2025-11-04",
    )

    assert context.period == ""
    assert context.row_index is None


def test_sentence_label_marks_multi_value_sentence_without_clipping_its_identity():
    label = shadow_sentence_label({
        "row_index": 11,
        "sentence": "배추(-34.5%), 무(-40.5%), 쌀(21.3%), 사과(21.6%), 달걀(6.9%)이다.",
    })

    assert label.startswith("#11 · 복수 수치 5개 ·")
    assert "달걀(6" not in label
