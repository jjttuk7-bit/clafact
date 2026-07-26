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
    assert "Store(" not in section
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
    assert 'button("연구 이력 저장"' in section
    assert "save_experiment_research_run(" in section
    assert source.index('button("연구 이력 저장"') < source.index(
        "save_experiment_research_run(", source.index('button("연구 이력 저장"')
    )
    assert 'ROOT / "data/research/verification_lab.db"' in source
    assert "ExperimentStore(" not in section


def test_research_history_metadata_matches_the_independent_hcx_comparison():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    helper = source[source.index("def save_experiment_research_run"):source.index("SAMPLES =")]

    assert '"article_hash": _sha256_text(context["article_text"])' in helper
    assert '"sentence_hash": _sha256_text(row.sentence)' in helper
    assert '"provider": "HCX"' in helper
    assert '"model": "HCX-005"' in helper
    assert '"prompt_version":' in helper
    assert '"python_ms": python_result.elapsed_ms' in helper
    assert '"hcx_ms": hcx_result.elapsed_ms' in helper
    assert '"hcx_calls": hcx_result.llm_calls' in helper
    assert '"hcx_status": row.hcx_status' in helper
    assert '"hcx_candidate": hcx_candidate' in helper
    assert '"evidence_status": row.hcx_evidence_status' in helper
    assert '"disagreement_class": row.disagreement_class' in helper