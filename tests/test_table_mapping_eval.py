from clafact.eval.table_mapping import evaluate_table_mapping


def test_evaluate_table_mapping_records_ranked_candidates_and_hit_metrics():
    rows = [
        {"candidate_id": "one", "sentence": "소비자물가 상승률", "gold_table_ids": ["T1"]},
        {"candidate_id": "two", "sentence": "두 표를 함께 써야 함", "gold_table_ids": ["T2", "T3"]},
        {"candidate_id": "skip", "sentence": "KOSIS 범위 밖", "gold_table_ids": []},
    ]

    def search(sentence: str, top_k: int):
        assert top_k == 3
        return {
            "소비자물가 상승률": [
                {"TBL_ID": "T1", "TBL_NM": "소비자물가"},
                {"TBL_ID": "X", "TBL_NM": "다른 표"},
            ],
            "두 표를 함께 써야 함": [
                {"TBL_ID": "T2", "TBL_NM": "첫 표"},
                {"TBL_ID": "X", "TBL_NM": "다른 표"},
                {"TBL_ID": "T3", "TBL_NM": "둘째 표"},
            ],
        }[sentence]

    result = evaluate_table_mapping(rows, search, top_k=3)

    assert result["summary"] == {
        "evaluated": 2,
        "skipped_no_kosis_gold": 1,
        "hit_any_at_1": 2,
        "hit_all_at_1": 1,
        "hit_any_at_k": 2,
        "hit_all_at_k": 2,
    }
    assert result["cases"][1]["candidate_table_ids"] == ["T2", "X", "T3"]
    assert result["cases"][1]["hit_all_at_k"] is True
