from pathlib import Path


def test_dashboard_uses_csv_file_uploader_and_separate_processing_button() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert 'st.file_uploader("CSV 기사 파일"' in source
    assert 'import_article_file(temporary_path, store)' in source
    assert '기사 파일 경로 (JSONL/CSV)' not in source
    assert '"대기 Claim 처리"' in source
