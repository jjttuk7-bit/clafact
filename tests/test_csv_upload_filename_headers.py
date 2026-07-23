from pathlib import Path


def test_dashboard_does_not_send_user_filename_in_http_headers() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '"X-Filename": uploaded_csv.name' not in source
    assert '"Content-Type": "text/csv"' in source
