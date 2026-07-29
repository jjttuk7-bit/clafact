from clafact.shadow_step_guide import build_shadow_step_guide, guide_next_action_text


def test_guide_starts_with_shadow_execution_when_no_run_exists():
    guide = build_shadow_step_guide()

    assert guide.completed_count == 0
    assert guide.next_step_id == "execute"
    assert [step.step_id for step in guide.steps] == [
        "execute", "select_sentence", "find_candidate", "compare_value", "review_export",
    ]
    assert guide.steps[0].state == "next"


def test_guide_moves_to_candidate_search_after_current_sentence_is_selected():
    guide = build_shadow_step_guide(
        shadow_run={"rows": [{"row_index": 1, "sentence": "물가가 2.4% 올랐다."}]},
        selected_row_index=1,
    )

    assert guide.completed_count == 2
    assert guide.next_step_id == "find_candidate"
    assert guide.steps[2].state == "next"


def test_guide_moves_to_actual_value_comparison_after_candidate_is_mapped():
    guide = build_shadow_step_guide(
        shadow_run={"rows": [{"row_index": 1, "sentence": "물가가 2.4% 올랐다."}]},
        selected_row_index=1,
        candidate_search_done=True,
        mappings=[{"row_index": 1, "evidence_id": "DT_CPI:year"}],
    )

    assert guide.completed_count == 3
    assert guide.next_step_id == "compare_value"
    assert guide.steps[3].state == "next"


def test_guide_marks_actual_comparison_complete_only_for_match_or_mismatch():
    guide = build_shadow_step_guide(
        shadow_run={"rows": [{"row_index": 1, "sentence": "물가가 2.4% 올랐다."}]},
        selected_row_index=1,
        candidate_search_done=True,
        mappings=[{"row_index": 1, "evidence_id": "DT_CPI:year"}],
        comparisons=[{"row_index": 1, "status": "not_comparable"}],
    )

    assert guide.completed_count == 3
    assert guide.next_step_id == "compare_value"
    assert guide.steps[3].state == "review_needed"


def test_guide_finishes_after_value_comparison_and_review_are_recorded():
    guide = build_shadow_step_guide(
        shadow_run={"rows": [{"row_index": 1, "sentence": "물가가 2.4% 올랐다."}]},
        selected_row_index=1,
        candidate_search_done=True,
        mappings=[{"row_index": 1, "evidence_id": "DT_CPI:year"}],
        comparisons=[{"row_index": 1, "status": "match"}],
        reviews=[{"row_index": 1, "action": "approve"}],
    )

    assert guide.completed_count == 5
    assert guide.next_step_id is None
    assert guide.steps[-1].state == "complete"


def test_guide_next_action_text_explains_actual_value_comparison():
    assert guide_next_action_text("compare_value") == "다음 할 일: KOSIS 근거를 연결하고 실제 값 대조를 실행하세요."