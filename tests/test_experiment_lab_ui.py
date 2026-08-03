from pathlib import Path


def test_streamlit_exposes_a_separate_verification_lab_without_store_writes():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert '"검증 실험실"' in source
    assert 'NAV_ITEMS = ("운영 홈", "검증", "검증자 리뷰", "플라이휠", "자산 현황", "검증 실험실")' in source
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    assert "운영 Claim·리뷰 큐·판정 이력을 변경하지 않습니다" in section
    assert "run_comparison" in section
    assert "Python 규칙만" in section
    assert "HCX-005만" in section
    assert "하이브리드" in section
    assert 'st.file_uploader("검증 실험실 CSV 파일"' in section
    assert 'key="experiment_lab_csv"' in section
    assert 'scan_csv_stream' in section
    assert "기사 본문 전체" in section
    assert 'prepare_eda' in section
    assert '기사 선택' in section
    assert '자동 일괄 실행하지 않습니다' in section
    assert '전체 비교 실행' in section
    assert 'Python만 실행' in section
    assert 'HCX만 실행' in section
    assert '하이브리드만 실행' in section
    assert 'HCX-005 실호출' in section
    assert 'HCX 후보 문장' in section
    assert 'HCX 근거 상태' in section
    assert '검색 필요' in section
    assert "미실행" in section
    assert "format_elapsed_ms" in source
    assert "CSV 통합 EDA" in section
    assert "데이터 품질" in section
    assert "기사 구조" in section
    assert "수치 주장 특성" in section
    assert "기사 탐색·상세" in section
    assert "EDA는 Python 규칙만 사용하며 HCX를 자동 호출하지 않습니다" in section
    assert "원본 행" in section
    assert '"CSV 전처리·EDA"' not in section
    assert 'st.bar_chart([len(article["body"]) for article in csv_articles])' not in section
    assert "MAX_EDA_ROWS" in section
    assert "resolve_eda_range" in section
    assert "store_upload_metadata" in section
    assert "prepare_eda" in section
    assert "filter_articles" in section
    assert "selected_article_rows" in section
    assert 'width="stretch"' in section
    assert "use_container_width=True" not in section[
        section.index('"CSV 통합 EDA"'):section.index("lab_date =")
    ]
    assert "Python 1차" in section
    assert '방식별 판단 근거' in section
    assert '전체 비교 경과시간' in section
    assert 'Store(ROOT / "data/service/clafact.db")' not in section
    assert "process_pending(" not in section


def test_eda_range_selection_is_explicit_and_large_files_do_not_auto_analyze():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index("# ═════════════ 탭 2: 검증자 리뷰")]
    eda = section[section.index("selected_lab_article = None"):section.index("lab_date =")]

    assert '"분석 범위 확정"' in eda
    assert "if lab_source_row_count > MAX_EDA_ROWS:" in eda
    assert "confirmed=range_submitted" in eda
    assert "if selected_eda_range is not None:" in eda
    assert "read_csv_range(lab_csv, selected_eda_range)" in eda
    assert "prepare_eda(" in eda
    assert "row_number_start=selected_eda_range.start" in eda
    assert "analysis_scope_caption(" in eda
    assert "전체" in eda


def test_empty_or_header_only_csv_uses_the_tested_controller_path():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[
        source.index('if view == "검증 실험실":'):source.index("lab_date =")
    ]

    assert "from clafact.experiment_eda_controller import prepare_eda" in source
    assert "empty_preparation = prepare_eda(())" in section
    assert 'if empty_preparation.status == "empty":' in section
    assert "st.warning(empty_preparation.user_message)" in section
    assert "prepared = prepare_eda(" in section
    assert "row_number_start=selected_eda_range.start" in section


def test_eda_analysis_boundary_wires_only_the_tested_python_controller():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index("selected_eda_range = None"):source.index("lab_date =")]

    forbidden = (
        "HcxClient",
        "judge_sentence",
        "ExperimentStore",
        "Store(",
        "process_pending(",
        "KosisClient",
        "KosisOpenApiClient",
    )
    assert all(name not in section for name in forbidden)
    assert "prepare_eda(" in section
    assert "analyze_rows(" not in section
    assert "build_eda_view(" not in section
    assert "selected_article_rows(" in section


def test_eda_ui_never_reintroduces_the_single_article_giant_body_bar():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[
        source.index('if view == "검증 실험실":'):source.index("lab_date =")
    ]

    assert 'structure_chart_mode == "single"' in section
    assert "의미 없는 분포 차트 대신 실제 정제·문장 지표" in section
    assert 'st.bar_chart([len(article["body"]) for article in csv_articles])' not in section
    assert 'bar_chart([article.clean_length' not in section
    assert 'bar_chart([len(article.cleaned_body)' not in section


def test_eda_uses_session_scoped_cache_and_resets_selection_outside_range():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index("# ═════════════ 탭 2: 검증자 리뷰")]
    eda = section[section.index("selected_lab_article = None"):section.index("lab_date =")]

    assert "cache_key(" in eda
    assert "EDA_CACHE_KEY" in eda
    assert "EDA_REPORT_KEY" in eda
    assert "EDA_VIEW_KEY" in eda
    assert "st.cache_data" not in eda
    assert "EDA_SELECTED_ARTICLE_KEY" in eda
    assert "selected_row_numbers" in eda
    assert "selected_lab_article" in eda
    assert "HcxClient" not in eda
    assert "process_pending(" not in eda


def test_full_comparison_exposes_disagreement_research_controls():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    for outcome in ("P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR"):
        assert outcome in section
    assert "건 ·" in section
    assert "HCX_ERROR는 의미적 미탐지(H-)에서 제외" in section
    assert 'st.selectbox("유형 필터"' in section
    assert "filtered_disagreement_rows" in section
    assert "Python 판단 근거" in section
    assert "HCX 판단 근거" in section
    assert '"연구 이력 저장"' in section
    assert "save_comparison_run(" in section
    assert section.index('"연구 이력 저장"') < section.index("save_comparison_run(")
    assert 'ROOT / "data/research/verification_lab.db"' in source
    assert "ExperimentStore(" in section
    assert "from clafact.experiment_store import ExperimentStore" in source


def _load_hcx_candidate_display():
    import ast

    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_hcx_candidate_display"),
        None,
    )
    assert function is not None, "HCX UI 상태 formatter가 필요합니다"
    namespace = {}
    ast.fix_missing_locations(function)
    exec(compile(ast.Module(body=[function], type_ignores=[]), "streamlit_app.py", "exec"), namespace)
    return namespace["_hcx_candidate_display"]


def test_hcx_candidate_display_separates_execution_errors_from_semantic_misses():
    display = _load_hcx_candidate_display()

    assert display(True, "success") == "탐지"
    assert display(False, "success") == "미탐지"
    assert display(None, "call_error") == "실행 실패 (call_error)"
    assert display(None, "parse_error") == "실행 실패 (parse_error)"
    assert display(None, "invalid_response") == "실행 실패 (invalid_response)"


def test_filtered_detail_uses_actual_python_reason_and_explicit_hcx_status():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    detail = section[section.index("filtered_disagreement_rows"):]

    assert 'python_reason = mode_results["python"].rows[number - 1].reason' in detail
    assert "**Python 판단 근거:**" in detail
    assert '_hcx_candidate_display(row.llm_verifiable, row.hcx_status)' in detail
    assert "**HCX 실행 상태:** {row.hcx_status}" in detail
    assert "**HCX 후보 판단 근거:**" in detail
    assert "**HCX 근거 판단:**" in detail


def test_full_comparison_reuses_execution_identity_and_guards_changed_input():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert section.count("build_run_context(") == 1
    assert "run_context.input_fingerprint" in section
    assert "input_matches_context(comparison_text, comparison_date, run_context)" in section
    assert "현재 입력이 이 전체 비교 실행의 입력과 달라 저장할 수 없습니다" in section
    assert "semantic_disagreement_count(result)" in section
    assert "의미 불일치 문장" in section
    assert "save_comparison_run(" in section
    assert 'st.session_state.get("experiment_lab_saved_run_id") == run_context.run_id' in section
    assert "disabled=save_disabled" in section


def test_saved_research_run_exposes_review_csv_and_explicit_golden_controls():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert "export_run_csv(" in section
    assert 'st.download_button(' in section
    assert '"현재 실행 CSV 다운로드"' in section
    assert "true_candidate" in section
    assert "false_positive" in section
    assert "hold" in section
    assert "reviewable_sentences(saved_sentences)" in section
    assert "pop_review_feedback(st.session_state)" in section
    assert "store_review_feedback(st.session_state" in section
    assert "save_human_review(" in section
    assert "save_human_review_clicked = st.button(" in section
    assert "save_human_review = st.button(" not in section
    assert '"사람 검토 저장"' in section
    assert "promote_reviewed_sentence(" in section
    assert '"승인 사례를 골든셋으로 승격"' in section
    assert 'ROOT / "data/goldenset/hybrid_disagreements_v0.jsonl"' in section
    assert section.index('"승인 사례를 골든셋으로 승격"') < section.index("promote_reviewed_sentence(")
    assert "정확도" not in section
    assert "build_reviewed_evaluation(saved_sentences, saved_run)" in section
    assert '"사람 검토 기반 평가"' in section
    assert "evaluation_display.reviewed_count" in section
    assert "evaluation_display.rows" in section
    assert "TP·FP·FN·TN을 함께 표시합니다" in section
    assert "‘산출 불가’" in section
    assert "독립 HCX 문장 판정 응답률" in section
    assert "evaluation_display.independent_hcx_response_success" in section
    assert "evaluation_display.independent_hcx_response_total" in section
    assert "evaluation_display.metric_scope_label" in section
    assert "전체 기사 문장 성능이 아닙니다" in section
    assert "evaluation_display.run_label" in section
    assert "HCX 오류 행은 HCX 정밀도·재현율 표본에서 제외" in section
    assert "Python OR HCX는 HCX 오류 시 Python 결과를 유지" in section


def test_historical_research_is_available_without_a_current_result():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    history = section[section.index('"누적 연구 이력"'):]

    assert "ExperimentStore(" in history
    assert "list_runs(" in history
    assert "get_sentences_for_runs(" in history
    assert "get_history_summary(" in history
    assert '"준비된 필터 CSV 다운로드"' in history
    assert "export_filtered_csv(" in history
    assert '"과거 실행 선택"' in history
    assert "save_human_review(" in history
    assert "promote_reviewed_sentence(" in history
    assert section.index('"누적 연구 이력"') > section.index("if result:")


def test_history_uses_exact_sql_pagination_and_lazy_bounded_export():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]
    history = section[section.index('"누적 연구 이력"'):]

    assert "get_history_filter_facets(" in history
    assert "get_history_summary(" in history
    assert "build_history_page(" in history
    assert "list_runs(" in history
    assert "limit=50" in history
    assert "st.number_input(" in history
    assert 'base_page["options"]' not in history
    assert "history_store.get_revision(" in history
    assert "revision=history_revision" in history
    assert "payload=filtered_export.payload" in history
    assert "row_count=filtered_export.row_count" in history
    assert "현재 업로드 입력은 재사용하지 않으며 연구 DB에 저장된 문장만 조회합니다." in history
    assert '"필터 CSV 준비"' in history
    assert history.index('"필터 CSV 준비"') < history.index("export_filtered_csv(")
    assert "MAX_FILTERED_EXPORT_ROWS" in history
    assert "list_all_runs(" not in history
    assert "export_runs_csv(" not in history
    assert 'scope="history"' in history


def test_streamlit_displays_upload_total_and_selected_analysis_interval_separately():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[
        source.index('if view == "검증 실험실":'):source.index("lab_date =")
    ]

    assert "analysis_scope_caption(" in section
    assert "lab_source_row_count" in section
    assert "selected_eda_range" in section
    assert 'st.caption(analysis_scope_caption(' in section
    assert 'f"분석 구간 ' not in section

def test_streamlit_converts_typed_csv_parser_failures_to_user_messages():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[
        source.index('if view == "검증 실험실":'):source.index("lab_date =")
    ]

    assert "EdaCsvReadError" in source
    assert section.count("except EdaCsvReadError as error:") >= 2
    assert section.count("st.error(error.user_message)") >= 2


def test_shadow_lab_loads_dotenv_and_exposes_hcx_connection_state():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증 실험실":'):source.index('# ═════════════ 탭 2: 검증자 리뷰')]

    assert 'load_runtime_env(ROOT / ".env")' in source
    assert 'hcx_status = hcx_runtime_status()' in section
    assert 'HCX 모드: 실연결 준비됨' in section
    assert 'HCX 모드: fixture' in section
