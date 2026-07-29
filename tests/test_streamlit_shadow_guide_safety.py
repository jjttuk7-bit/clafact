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