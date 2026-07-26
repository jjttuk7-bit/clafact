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
    assert 'csv.DictReader' in section
    assert '"기사 본문 전체"' in section
    assert 'clean_uploaded_article_body' in section
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
    assert "원본 행" in section
    assert "st.bar_chart" in section
    assert "Python 1차" in section
    assert '방식별 판단 근거' in section
    assert '전체 비교 경과시간' in section
    assert 'Store(ROOT / "data/service/clafact.db")' not in section
    assert "process_pending(" not in section


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
    assert 'row["disagreement_class"] in {"P+/H-", "P-/H+"}' in section
    assert 'st.session_state.pop("experiment_lab_research_feedback"' in section
    assert 'st.session_state["experiment_lab_research_feedback"]' in section
    assert "update_review(" in section
    assert '"사람 검토 저장"' in section
    assert "promote_to_golden(" in section
    assert '"승인 사례를 골든셋으로 승격"' in section
    assert 'ROOT / "data/goldenset/hybrid_disagreements_v0.jsonl"' in section
    assert section.index('"승인 사례를 골든셋으로 승격"') < section.index("promote_to_golden(")
    assert "정확도" not in section
    assert "재현율" not in section
