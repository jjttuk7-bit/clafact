from types import SimpleNamespace

from clafact.experiment_research import (
    build_run_context,
    input_matches_context,
    save_comparison_run,
    semantic_disagreement_count,
)
from clafact.experiment_store import ExperimentStore


def _comparison_result():
    specifications = [
        (True, True, "success", "P+/H+"),
        (True, False, "success", "P+/H-"),
        (False, True, "success", "P-/H+"),
        (False, False, "success", "P-/H-"),
        (True, None, "call_error", "HCX_ERROR"),
    ]
    rows = []
    python_rows = []
    for index, (python_candidate, hcx_candidate, hcx_status, outcome) in enumerate(specifications, start=1):
        sentence = f"문장 {index}은 {index}% 변했다."
        rows.append(SimpleNamespace(
            sentence=sentence,
            python_candidate=python_candidate,
            llm_verifiable=hcx_candidate,
            llm_reason=f"HCX 사유 {index}",
            hcx_status=hcx_status,
            hcx_evidence_status="needs_retrieval",
            disagreement_class=outcome,
        ))
        python_rows.append(SimpleNamespace(reason=f"Python 사유 {index}"))
    return SimpleNamespace(
        rows=rows,
        mode_results={
            "python": SimpleNamespace(rows=python_rows, elapsed_ms=3, llm_calls=0),
            "llm": SimpleNamespace(rows=[], elapsed_ms=101, llm_calls=5),
            "hybrid": SimpleNamespace(rows=[], elapsed_ms=88, llm_calls=4),
        },
        elapsed_ms=205,
        llm_calls=9,
    )


def test_run_context_keeps_stable_identity_and_detects_changed_input():
    context = build_run_context(
        article_text="물가는 2.4% 올랐다.",
        article_date="2025-11-04",
        article_title="소비자물가",
        source_row_count=1,
        prompt_version="candidate-v2",
        created_at="2026-07-26T12:00:00+09:00",
        run_token="fixed-token",
    )

    assert context.run_id.startswith("vlab-")
    assert context.run_id.endswith("-fixed-token")
    assert len(context.input_fingerprint) == 64
    assert input_matches_context("물가는 2.4% 올랐다.", "2025-11-04", context)
    assert not input_matches_context("물가는 2.5% 올랐다.", "2025-11-04", context)
    assert not input_matches_context("물가는 2.4% 올랐다.", "2025-11-05", context)


def test_explicit_save_is_idempotent_and_persists_total_calls_and_every_class(tmp_path):
    database_path = tmp_path / "research" / "verification_lab.db"
    operating_database_path = tmp_path / "data" / "service" / "clafact.db"
    result = _comparison_result()
    context = build_run_context(
        article_text=" ".join(row.sentence for row in result.rows),
        article_date="2025-11-04",
        article_title="소비자물가",
        source_row_count=1,
        prompt_version="candidate-v2",
        created_at="2026-07-26T12:00:00+09:00",
        run_token="fixed-token",
    )

    first = save_comparison_run(database_path, result, context)
    second = save_comparison_run(database_path, result, context)

    assert first.created is True
    assert second.created is False
    assert first.run_id == second.run_id == context.run_id
    with ExperimentStore(database_path) as store:
        saved_run = store.get_run(context.run_id)
        saved_sentences = store.get_sentences(context.run_id)
        run_count = store.conn.execute("SELECT COUNT(*) FROM experiment_runs").fetchone()[0]
    assert saved_run["hcx_calls"] == result.llm_calls == 9
    assert saved_run["python_ms"] == 3
    assert saved_run["hcx_ms"] == 101
    assert saved_run["total_ms"] == 205
    assert saved_run["source_row_count"] == 1
    assert saved_run["provider"] == "HCX"
    assert saved_run["model"] == "HCX-005"
    assert saved_run["prompt_version"] == "candidate-v2"
    assert saved_run["sentence_count"] == 5
    assert run_count == 1
    assert [row["disagreement_class"] for row in saved_sentences] == [
        "P+/H+", "P+/H-", "P-/H+", "P-/H-", "HCX_ERROR"
    ]
    assert saved_sentences[-1]["hcx_candidate"] is None
    assert saved_sentences[-1]["hcx_status"] == "call_error"
    assert saved_sentences[0]["python_reason"] == "Python 사유 1"
    assert saved_sentences[0]["hcx_reason"] == "HCX 사유 1"
    assert not operating_database_path.exists()


def test_semantic_difference_excludes_agreement_and_hcx_errors():
    assert semantic_disagreement_count(_comparison_result()) == 2

def test_concurrent_identical_saves_are_atomic_and_idempotent(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading

    database_path = tmp_path / "research" / "verification_lab.db"
    result = _comparison_result()
    context = build_run_context(
        article_text=" ".join(row.sentence for row in result.rows),
        article_date="2025-11-04",
        article_title="소비자물가",
        source_row_count=1,
        prompt_version="candidate-v2",
        created_at="2026-07-26T12:00:00+09:00",
        run_token="concurrent-token",
    )
    start = threading.Barrier(2)

    def save_once():
        start.wait()
        return save_comparison_run(database_path, result, context)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: save_once(), range(2)))

    assert sorted(outcome.created for outcome in outcomes) == [False, True]
    with ExperimentStore(database_path) as store:
        assert len(store.list_runs()) == 1
        assert len(store.get_sentences(context.run_id)) == len(result.rows)


def test_same_run_id_with_conflicting_payload_is_rejected(tmp_path):
    import pytest
    from dataclasses import replace

    database_path = tmp_path / "research.db"
    result = _comparison_result()
    context = build_run_context(
        article_text=" ".join(row.sentence for row in result.rows),
        article_date="2025-11-04",
        article_title="원본 제목",
        source_row_count=1,
        prompt_version="candidate-v2",
        created_at="2026-07-26T12:00:00+09:00",
        run_token="conflict-token",
    )
    save_comparison_run(database_path, result, context)

    with pytest.raises(ValueError, match="run_id.*payload|실행 ID.*다른"):
        save_comparison_run(
            database_path, result, replace(context, article_title="충돌 제목")
        )
