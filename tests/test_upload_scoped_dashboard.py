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
    assert 'KOSIS 분석 대상' in home
    assert '자동 검증 가능' in home
    assert '복합 KOSIS 사람 검토' in home
    assert '별도 근거 확인 대상' in home
    assert '누적 등록 기사' in home

def test_operations_home_breaks_out_non_kosis_routes() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert '공식 공지' in home
    assert '비KOSIS 공식자료' in home
    assert '민간·플랫폼' in home
    assert '사람 검토' in home

def test_operations_home_hides_manual_policy_reclassification():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "\uc804\uccb4 \uc0c8 \uc815\ucc45 \uc801\uc6a9" not in home
    assert "reclassify_all_claims" not in home


def test_verification_tab_shows_unverifiable_reason_summary():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    verification_section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert "\ud310\ub2e8\ubd88\uac00 \uc0ac\uc720" in verification_section
    assert 'label="unverifiable"' in verification_section

def test_operations_home_shows_registration_progress_stages():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "파일 읽기" in home
    assert "기사 등록" in home
    assert "출처 분류" in home
    assert "검증 후보 준비" in home
    assert "st.status" in home

def test_operations_home_explains_kosis_analysis_and_review_routes() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "KOSIS 분석 대상은 직접 조회형과 복합형을 모두 포함합니다" in home
    assert "복합 KOSIS는 KOSIS 분석 후 최종 판정만 사람이 검토합니다" in home


def test_operations_home_uses_a_clear_workflow_hierarchy() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "ops-workspace" in home
    assert "ops-summary-grid" in home
    assert "ops-route-grid" in home
    assert "ops-next-action" in home
    assert 'type="primary"' in home


def test_operations_home_labels_the_three_routing_cards() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "자동 검증 가능" in home
    assert "복합 KOSIS 사람 검토" in home
    assert "별도 근거 확인" in home


def test_verification_tab_uses_a_clear_workflow_hierarchy() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert "verification-summary-grid" in section
    assert "verification-workspace" in section
    assert "verification-action-bar" in section
    assert "검증 현황" in section


def test_verification_tab_keeps_batch_action_prominent() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert "현재 페이지 50건 검증" in section
    assert "대기" in section
    assert "검증 대기" in section
    assert "판단불가" in section


def test_verification_tab_groups_claim_selection_controls() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert "verification-controls" in section
    assert "verification-claim-context" in section
    assert "검증 대상 선택" in section
    assert "선택한 기사" in section


def test_selected_article_mode_offers_a_next_verification_action() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert "선택 기사 검증 실행" in section
    assert "pending_selected_ids" in section
    assert 'key="verify_selected_article"' in section


def test_operations_home_shows_kosis_claim_extraction_preview() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "KOSIS 수치 주장 추출 결과" in home
    assert "claim_previews" in home
    assert "추출 수치" in home
    assert "출처 분류" in home


def test_operations_home_shows_article_date_for_extraction_preview() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "기사 등록일" in home
    assert "article_date" in home


def test_operations_home_can_reset_current_upload_state() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "새 업로드 시작" in home
    assert "uploader_key" in home
    assert 'pop("uploaded_article_ids"' in home
    assert 'pop("upload_summary"' in home


def test_operations_home_resets_previous_preview_when_file_changes() -> None:
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    home = source[source.index('if view == "운영 홈":'):source.index('# ═════════════ 탭 1: 검증')]

    assert "_upload_file_signature" in home
    assert "uploaded_csv.name" in home
