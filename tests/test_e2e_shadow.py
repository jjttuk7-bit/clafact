from clafact.e2e_shadow import e2e_comparisons_by_row


def test_attaches_matching_e2e_verdict_to_shadow_sentence_row():
    run = {"rows": [{"row_index": 1, "sentence": "분유 물가가 3.4% 올랐다."}]}
    verdicts = [{
        "sentence": "분유 물가가 3.4% 올랐다.", "verdict": "match", "claimed": 3.4,
        "official": 3.3745, "reason": "원본 계산값 일치", "snapshot_ids": ["base", "current"],
    }]

    attached = e2e_comparisons_by_row(run, verdicts)

    assert attached[1][0]["status"] == "match"
    assert attached[1][0]["snapshot_id"] == "base | current"
