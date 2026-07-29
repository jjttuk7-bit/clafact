from pathlib import Path


def test_candidate_history_default_exists_before_guide_store_reads():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")
    guide_scope = source[source.index("candidate_row = candidate_sentence_options[candidate_sentence_label]"):]

    default_index = guide_scope.index("guide_candidate_runs = []")
    store_read_index = guide_scope.index(
        'with KosisShadowMappingStore(ROOT / "data/research/kosis_shadow_mapping.db")'
    )

    assert default_index < store_read_index