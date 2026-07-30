from pathlib import Path


def test_candidate_history_default_exists_before_guide_store_reads():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")
    guide_scope = source[source.index("candidate_row = candidate_sentence_options[candidate_sentence_label]"):]

    default_index = guide_scope.index("guide_candidate_runs = []")
    store_read_index = guide_scope.index(
        'with KosisShadowMappingStore(ROOT / "data/research/kosis_shadow_mapping.db")'
    )

    assert default_index < store_read_index

def test_shadow_mode_places_the_current_guide_hint_at_each_action_area():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    assert source.count('guide.screen_hint.step_id') >= 3
    assert 'guide.screen_hint.message' in source

def test_shadow_actual_value_comparison_displays_gate_results():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    assert 'st.markdown("###### 대조 게이트")' in source
    assert 'comparison_display.get("gate_results", ())' in source
    assert '"통과" if gate.get("passed") else "실패"' in source

def test_candidate_apply_guides_to_kosis_snapshot_preparation():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    assert '"KOSIS 조회·스냅샷 준비"' in source
    assert 'prepare_kosis_snapshot_context' in source
    assert 'KOSIS 조회·스냅샷 준비를 계속하세요.' in source


def test_candidate_apply_clears_stale_snapshot_before_setting_prefill():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")
    candidate_apply_scope = source[source.index('if st.button("선택 후보를 근거 입력에 적용"'):]

    clear_snapshot_index = candidate_apply_scope.index(
        'st.session_state.pop("kosis_evidence_snapshot_context", None)'
    )
    set_prefill_index = candidate_apply_scope.index('st.session_state["kosis_evidence_prefill_pending"] =')

    assert clear_snapshot_index < set_prefill_index


def test_shadow_actual_value_comparison_renders_read_only_official_value_card():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    assert "build_value_comparison_card" in source
    assert "comparison_card = build_value_comparison_card(" in source
    card_scope = source[source.index("comparison_card = build_value_comparison_card("):]
    assert "snapshot=comparison_snapshot" in card_scope
    assert "snapshot=latest_snapshot" not in card_scope
    assert 'evidence_indicator=selected_evidence["indicator"]' in source
    assert 'evidence_selection=selected_evidence["source_selection"]' in source
    assert 'if comparison_card.alternatives:' in source
    assert 'st.expander("다른 공식 값 후보 보기")' in source
    for label in ("문장 값 / KOSIS 값", "비교 상태", "대조 근거", "기간", "지표", "선택 조건", "단위", "스냅샷 ID", "조회 시각"):
        assert label in source


def test_shadow_value_card_uses_the_snapshot_referenced_by_comparison_result():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    assert "comparison_snapshot = next(" in source
    assert 'snapshot.get("snapshot_id") == comparison_for_card.snapshot_id' in source
    assert "snapshot=comparison_snapshot" in source
    assert "대조 결과가 가리키는 KOSIS 스냅샷을 찾지 못해 후보 카드를 표시하지 않습니다." in source

def test_shadow_mode_exposes_read_only_goldenset_seed_status_and_downloads():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    assert 'st.expander("골든셋 Seed 100 현황"' in source
    assert '"골든셋 CSV 템플릿 다운로드"' in source
    assert '"골든셋 검증 결과 다운로드"' in source

def test_goldenset_status_is_between_the_step_guide_and_candidate_search_controls():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    guide_index = source.index('with st.expander("연구 진행 가이드"')
    goldenset_index = source.index('with st.expander("골든셋 Seed 100 현황"')
    candidate_heading_index = source.index('st.markdown("##### KOSIS 후보 탐색")')
    candidate_selectbox_index = source.index('"후보를 찾을 Shadow 문장"')

    assert guide_index < goldenset_index < candidate_heading_index < candidate_selectbox_index


def test_goldenset_status_loads_jsonl_and_surfaces_semantic_parity_as_research_validation():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")

    assert "load_jsonl(research_goldenset.SEED_JSONL_PATH)" in source
    assert "validate_semantic_parity(goldenset_rows, goldenset_jsonl_rows)" in source
    assert "additional_issues=goldenset_parity_issues" in source
    assert "Shadow 실행과 후보 탐색은 계속 사용할 수 있습니다" in source


def test_shadow_review_keeps_reviewed_rows_available_for_correction():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")

    assert 'row["review_state"] in {"needs_review", "reviewed", "hold"}' in source
