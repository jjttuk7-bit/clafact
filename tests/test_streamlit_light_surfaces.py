from pathlib import Path


def test_dashboard_defines_theme_aware_surface_tokens() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "color-scheme:light dark" in source
    assert "--ops-page:var(--background-color,#F3F6F8)" in source
    assert "--ops-surface:var(--secondary-background-color,#FFFFFF)" in source
    assert "--ops-border:color-mix" in source
