from pathlib import Path


def test_shadow_mode_renders_current_and_golden_semantic_summary_cards():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('with shadow_lab_tab:'):source.index('st.markdown("##### 과거 Shadow 실행 비교")')]

    assert 'st.markdown("##### 현재 구현된 Semantic 검증 상태")' in section
    assert 'current_semantic_summary(' in section
    assert 'st.markdown("##### 골든셋 E2E 전체 현황")' in section
    assert 'e2e_semantic_summary(e2e_verdicts)' in section
    assert 'data/reference/e2e_semantic_summary_latest.json' in section
    assert '배포용 E2E 결과 스냅샷' in section
    assert 'Claim 완료' in section
    assert 'export_shadow_run_csv(' in section
