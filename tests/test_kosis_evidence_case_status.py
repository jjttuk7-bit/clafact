from clafact.kosis_evidence_case_status import build_evidence_case_status


def test_case_status_shows_next_action_until_shadow_mapping_exists():
    status = build_evidence_case_status(
        evidence={"table_id": "DT_1B040A3", "snapshot_id": "kosis-123"},
        snapshot_count=1,
        mapping_count=0,
        pending_review_count=0,
    )

    assert status.completed_steps == 2
    assert status.next_action == "Shadow 문장을 이 근거 객체에 연결하세요."


def test_case_status_is_complete_after_mapping_and_no_pending_revision_review():
    status = build_evidence_case_status(
        evidence={"table_id": "DT_1B040A3", "snapshot_id": "kosis-123"},
        snapshot_count=1,
        mapping_count=2,
        pending_review_count=0,
    )

    assert status.completed_steps == 4
    assert status.next_action == "첫 실제 근거 객체 사례가 완성되었습니다."
