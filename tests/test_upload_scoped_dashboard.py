from pathlib import Path


def test_dashboard_scopes_processing_and_audit_rows_to_uploaded_articles() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert 'st.session_state["uploaded_article_ids"]' in source
    assert 'WHERE c.article_id IN' in source


def test_dashboard_shows_upload_summary_only_after_article_registration() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    registration_index = source.index('if st.button("기사 등록"')
    upload_summary_index = source.index('if uploaded_article_ids:')
    assert registration_index < upload_summary_index
    assert 'KOSIS 검증 후보' in source

def test_verification_tab_reads_saved_results_from_the_current_upload():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    verification_section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    assert '이번 업로드 검증 결과' in verification_section
    assert 'fetch_upload_results(uploaded_article_ids, route="KOSIS_RETRIEVAL")' in verification_section
    assert '데모 샘플 직접 검증' in verification_section

def test_dashboard_keeps_reviewer_tab_as_an_executable_branch():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '# ═════════════ 탭 2: 검증자 리뷰 (WF-2) ═════════════\nif view == "검증자 리뷰":' in source

def test_verification_tab_offers_all_claim_view_with_filters_and_pagination():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    verification_section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    assert '전체 수치 주장' in verification_section
    assert '수치 주장 검색' in verification_section
    assert '50건씩' in verification_section
    assert 'count_upload_results' in verification_section

def test_dashboard_custom_colors_follow_streamlit_theme_tokens():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '--ops-page:var(--background-color' in source
    assert '--ops-surface:var(--secondary-background-color' in source
    assert '--ops-text:var(--text-color' in source
    assert 'background:var(--ops-surface)' in source

def test_dashboard_resolves_custom_colors_inside_streamlit_theme_containers():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '.stApp { --ops-page:var(--background-color)' in source
    assert '[data-testid="stSidebar"] { --ops-page:var(--background-color)' in source

def test_verification_tab_explains_official_announcements_outside_kosis() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    verification_section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert 'OFFICIAL_ANNOUNCEMENT' in verification_section
    assert 'KOSIS 표 해당 없음 · 공식 공지 검증' in verification_section
    assert '공식 근거 확인 필요' in verification_section
def test_official_announcement_card_offers_evidence_registration() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    assert '공식 기관명' in source
    assert '공식 공지 URL' in source
    assert '시행일' in source
    assert '공식 공지 검증' in source