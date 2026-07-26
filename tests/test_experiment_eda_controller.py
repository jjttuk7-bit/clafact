from __future__ import annotations

from dataclasses import fields

from clafact import kosis, llm
from clafact import experiment_store
from clafact.experiment_eda_controller import prepare_eda
from clafact.pipeline import detect_llm
from clafact.service import batch
from clafact.service import store as service_store


EMPTY_MESSAGE = "CSV에 분석할 데이터 행이 없습니다."


def _forbidden(*args, **kwargs):
    raise AssertionError("EDA controller touched an external engine or store")


def test_empty_rows_return_explicit_status_without_calling_analysis():
    def forbidden_analysis(*args, **kwargs):
        raise AssertionError("empty/header-only CSV must not call analyze_rows")

    prepared = prepare_eda((), analyze_fn=forbidden_analysis)

    assert prepared.status == "empty"
    assert prepared.user_message == EMPTY_MESSAGE
    assert prepared.report is None
    assert prepared.view is None


def test_ready_rows_use_only_python_eda_modules(monkeypatch):
    monkeypatch.setattr(llm, "HcxClient", _forbidden)
    monkeypatch.setattr(detect_llm, "judge", _forbidden)
    monkeypatch.setattr(detect_llm, "judge_decision", _forbidden)
    monkeypatch.setattr(service_store, "Store", _forbidden)
    monkeypatch.setattr(experiment_store, "ExperimentStore", _forbidden)
    monkeypatch.setattr(batch, "process_pending", _forbidden)
    monkeypatch.setattr(kosis, "HttpKosisClient", _forbidden)
    monkeypatch.setattr(kosis, "FixtureKosisClient", _forbidden)
    monkeypatch.setattr(kosis, "CachedKosisClient", _forbidden)

    rows = (
        {
            "title": "업로드 기사",
            "date": "2025-11-04",
            "body": "소비자물가는 2.4% 상승했다.",
        },
    )
    prepared = prepare_eda(rows, row_number_start=101)

    assert prepared.status == "ready"
    assert prepared.user_message == ""
    assert prepared.report is not None
    assert prepared.view is not None
    assert prepared.report.articles[0].row_number == 101
    assert prepared.report.articles[0].sentences[0].text == rows[0]["body"]


class _BrokenBody:
    def __str__(self):
        raise ValueError("broken body")


def test_controller_isolates_bad_rows_and_problem_view_never_contains_bodies():
    raw_secret = "문제 표에 노출되면 안 되는 전체 원문"
    rows = (
        {"title": "오류", "date": "2025-11-04", "body": _BrokenBody()},
        {"title": "후속", "date": "2025-11-05", "body": raw_secret},
    )

    prepared = prepare_eda(rows, row_number_start=7)

    assert prepared.status == "ready"
    assert prepared.report is not None
    assert prepared.view is not None
    assert [article.row_number for article in prepared.report.articles] == [8]
    problem = prepared.view.problem_rows.rows[0]
    assert problem.row_number == 7
    assert {field.name for field in fields(problem)} == {"row_number", "title", "issue"}
    assert not hasattr(problem, "raw_body")
    assert not hasattr(problem, "cleaned_body")
    assert raw_secret not in repr(prepared.view.problem_rows)