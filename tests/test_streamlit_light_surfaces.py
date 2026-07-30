from pathlib import Path


def test_dashboard_defines_theme_aware_surface_tokens() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "color-scheme:light dark" in source
    assert "--ops-page:var(--background-color,#F3F6F8)" in source
    assert "--ops-surface:var(--secondary-background-color,#FFFFFF)" in source
    assert "--ops-border:color-mix" in source


def test_dashboard_uses_a_bounded_kosis_ui_profile_and_retry_guidance() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "UI_KOSIS_TIMEOUT_SECONDS = 5" in source
    assert "UI_KOSIS_MAX_OBJL_REPAIRS = 1" in source
    assert "max_objl_repairs=UI_KOSIS_MAX_OBJL_REPAIRS" in source
    assert "다시 시도" in source


def test_dashboard_limits_kosis_connection_retries_and_classifies_retry_errors() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "UI_KOSIS_MAX_CONNECTION_ATTEMPTS = 1" in source
    assert "max_connection_attempts=UI_KOSIS_MAX_CONNECTION_ATTEMPTS" in source
    assert "metadata_limit=3" in source
    assert "KOSIS 연결 지연" in source
    assert "KOSIS 표 파라미터 확인 필요" in source
    assert "KOSIS 호출 예산 소진" in source
