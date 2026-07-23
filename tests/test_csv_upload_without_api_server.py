from pathlib import Path


def test_dashboard_registers_csv_without_local_fastapi_server() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "from backend.app.ingest_service import import_article_file" in source
    assert "import_article_file(temporary_path, store)" in source
    assert 'f"{api_url}/internal/articles/upload"' not in source
