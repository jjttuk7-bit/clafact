from pathlib import Path


def test_dashboard_defines_distinct_light_and_dark_surface_tokens() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "--ops-page:#F3F6F8" in source
    assert "--ops-surface:#FFFFFF" in source
    assert "--ops-border:#C8D4DC" in source
    assert "@media (prefers-color-scheme: dark)" in source
