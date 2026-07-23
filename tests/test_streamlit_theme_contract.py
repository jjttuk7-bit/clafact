from pathlib import Path


def test_dashboard_styles_do_not_force_light_text_on_all_paragraphs() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "h1,h2,h3,p,label" not in source
    assert "div.stButton > button p { color:inherit !important; }" in source
    assert "background:var(--ops-page)" in source
