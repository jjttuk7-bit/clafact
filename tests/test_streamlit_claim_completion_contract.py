from pathlib import Path


def test_shadow_screen_offers_explicit_claim_completion_and_csv_export():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '"Claim 완료"' in source
    assert "ClaimCompletionStore" in source
    assert "complete_selected_claim" in source
    assert "completed_claims_by_row" in source
