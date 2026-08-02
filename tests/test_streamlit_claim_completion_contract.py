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

def test_shadow_screen_can_load_one_of_the_recent_twenty_saved_runs():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "list_runs(limit=20)" in source
    assert '"저장된 Shadow 실행 불러오기"' in source
    assert 'st.session_state["shadow_lab_run_id"]' in source