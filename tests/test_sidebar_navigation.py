from pathlib import Path


def test_app_uses_sidebar_navigation_and_scoped_experiment_tabs() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert "st.sidebar.radio(" in source
    assert all(label in source for label in ("운영 홈", "검증", "검증자 리뷰", "플라이휠", "자산 현황"))
    assert 'st.tabs(("기존 비교 실험", "Shadow Mode"))' in source
