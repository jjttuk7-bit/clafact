from pathlib import Path


def test_dashboard_scopes_processing_and_audit_rows_to_uploaded_articles() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert 'st.session_state["uploaded_article_ids"]' in source
    assert 'article_ids=uploaded_article_ids' in source
    assert 'WHERE c.article_id IN' in source


def test_dashboard_shows_processing_controls_only_after_article_registration() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    registration_index = source.index('if a.button("기사 등록"')
    process_mode_index = source.index('process_mode = st.radio')
    assert registration_index < process_mode_index
    assert source.index('limit = st.number_input') > registration_index
    assert 'if uploaded_article_ids:\n        process_mode = st.radio' in source