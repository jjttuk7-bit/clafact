from clafact.shadow_ui import download_filenames, execution_status_summary, shadow_database_path, shadow_input_defaults, shadow_result_rows, summary_metrics, llm_attempt_summary, validate_shadow_input


def test_shadow_database_path_is_research_only(tmp_path):
    assert shadow_database_path(tmp_path) == tmp_path / "data" / "research" / "shadow_lab.db"


def test_validate_shadow_input_rejects_blank_body():
    assert validate_shadow_input("   ") == "분석할 기사 본문을 입력해 주세요."
    assert validate_shadow_input("2025년 인구는 5,000만 명이다.") is None


def test_summary_metrics_returns_safe_display_numbers():
    assert summary_metrics({"row_count": "2", "review_count": None, "llm_calls": 1, "elapsed_ms": "15"}) == {
        "row_count": 2,
        "review_count": 0,
        "llm_calls": 1,
        "elapsed_ms": 15,
    }


def test_shadow_result_rows_flattens_saved_run_for_display():
    rows = shadow_result_rows({
        "rows": [{
            "row_index": 1,
            "sentence": "인구 문장",
            "baseline": {"python_candidate": True},
            "shadow": {"llm_candidate": False, "hybrid_candidate": True},
            "risk_reasons": ["candidate_conflict"],
            "review_state": "needs_review",
        }],
    })

    assert rows == [{
        "번호": 1,
        "문장": "인구 문장",
        "Python 후보": True,
        "LLM 후보": False,
        "Hybrid 후보": True,
        "위험 신호": "candidate_conflict",
        "검토 상태": "needs_review",
    }]

def test_download_filenames_include_run_id():
    assert download_filenames("shadow-123") == ("shadow-123.json", "shadow-123.csv")

def test_shadow_input_defaults_prefill_selected_csv_article():
    defaults = shadow_input_defaults(
        {"body": "CSV에서 고른 기사 본문", "date": "2026-07-20", "title": "선택 기사"},
        fallback_date="2026-07-28",
    )

    assert defaults == {
        "text": "CSV에서 고른 기사 본문",
        "article_date": "2026-07-20",
        "title": "선택 기사",
    }


def test_shadow_input_defaults_returns_none_without_selected_article():
    assert shadow_input_defaults(None, fallback_date="2026-07-28") is None

def test_execution_status_summary_marks_hcx_not_configured():
    summary = execution_status_summary({
        "rows": [{"shadow": {"hcx_status": "not_configured"}}],
    })

    assert summary == {
        "label": "HCX 미설정 · AI 판정 미사용",
        "detail": "HCX 상태: not_configured 1건",
        "severity": "warning",
        "response_rows": 0,
        "total_rows": 1,
    }


def test_execution_status_summary_marks_successful_hcx_response():
    summary = execution_status_summary({
        "rows": [{"shadow": {"hcx_status": "success"}}],
    })

    assert summary["label"] == "HCX 응답 완료"
    assert summary["severity"] == "success"
    assert summary["response_rows"] == 1
    assert summary["total_rows"] == 1

def test_llm_attempt_summary_separates_planned_paths_from_actual_responses():
    summary = llm_attempt_summary({
        "summary": {"llm_calls": 27},
        "rows": [
            {"shadow": {"hcx_status": "not_configured"}},
            {"shadow": {"hcx_status": "not_configured"}},
        ],
    })

    assert summary == {"attempt_paths": 27, "actual_responses": 0, "total_rows": 2}