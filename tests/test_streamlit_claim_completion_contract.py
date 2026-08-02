from pathlib import Path


def test_shadow_screen_offers_explicit_claim_completion_and_csv_export():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '"Claim 완료"' in source
    assert "ClaimCompletionStore" in source
    assert "complete_selected_claim" in source
    assert "completed_claims_by_row" in source


def test_shadow_completion_options_keep_distinct_evidence_and_scope_result_to_sentence():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "{evidence_id}" in source
    assert "selected_completed_claims = [" in source


def test_shadow_flow_places_candidate_search_before_evidence_management():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "저장된 Shadow 실행 불러오기" not in source
    assert source.index("##### KOSIS 후보 탐색") < source.index("##### KOSIS 통계표 근거 입력")
    assert source.index("##### KOSIS 통계표 근거 입력") < source.index("##### KOSIS 근거 연결")

def test_shadow_flow_saves_reviewed_evidence_before_value_comparison():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert source.index('"KOSIS 근거 연결 저장"') < source.index('"KOSIS 실제 값 대조"')
    assert 'item["evidence_id"] == selected_completion["mapping"]["evidence_id"]' in source
    assert 'item["snapshot_id"] == selected_completion["snapshot"]["snapshot_id"]' in source