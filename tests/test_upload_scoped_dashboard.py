from pathlib import Path


def test_dashboard_scopes_processing_and_audit_rows_to_uploaded_articles() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert 'st.session_state["uploaded_article_ids"]' in source
    assert 'fetch_upload_results(uploaded_article_ids' in source


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
def test_reviewer_tab_reads_persisted_review_queue() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증자 리뷰":'):source.index('# ═════════════ 탭 3: 플라이휠')]
    assert 'review_queue()' in section
    assert '자동 판정 승인' in section
    assert '판단 보류' in section
def test_verification_tab_offers_current_page_batch_verification() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    assert '현재 페이지 50건 검증' in section
    assert 'claim_ids=' in section
def test_reviewer_tab_offers_official_evidence_replacement() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증자 리뷰":'):source.index('# ═════════════ 탭 3: 플라이휠')]
    assert '공식 근거 교체 후 재검증' in section
    assert 'review_notice_url_' in section
def test_operations_home_explains_preprocessing_not_audit_log() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]
    assert '이번 업로드 전처리 요약' in home
    assert '원본 → 유효 기사 → 문장 → 수치 주장' in home
    assert '이번 업로드 감사 로그' not in home
def test_operations_home_shows_routing_funnel() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]
    assert 'KOSIS 자동 검증 대상' in home
    assert '별도 근거 확인 대상' in home
    assert '누적 등록 기사' in home

def test_operations_home_breaks_out_non_kosis_routes() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert '공식 공지' in home
    assert '비KOSIS 공식자료' in home
    assert '민간·플랫폼' in home
    assert '사람 검토' in home