from pathlib import Path


def test_dashboard_processes_pending_claims_without_local_fastapi_server() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "from clafact.service.batch import process_pending" in source
    assert "process_pending(batch_store, index, client, claim_ids=pending_ids[:50])" in source
    assert "process_pending(selected_store, index, client, claim_ids=pending_selected_ids)" in source
    assert 'f"{api_url}/internal/batches/process-pending"' not in source
