import csv
import io
import json

from clafact.pipeline.detect_llm import HcxDecision
from clafact.shadow_export import export_shadow_run_csv, export_shadow_run_json
from clafact.shadow_policy import ShadowPolicy
from clafact.shadow_service import ShadowLabService


def _judge(_: str) -> HcxDecision:
    return HcxDecision(False, "=제외 사유", "unknown", "", [])


def _saved_run(tmp_path):
    service = ShadowLabService(tmp_path / "shadow_lab.db")
    service.execute(
        "2025년 인구는 5,000만 명이다.", "2026-07-28", ShadowPolicy.default(),
        judge_fn=_judge, run_id="shadow-export-1", created_at="2026-07-28T10:00:00+09:00",
    )
    service.review(
        "shadow-export-1", 1, action="hold", note="=기간 확인", reviewed_at="2026-07-28T10:01:00+09:00"
    )
    return service


def test_json_export_keeps_policy_summary_rows_and_review_history(tmp_path):
    with _saved_run(tmp_path) as service:
        payload = export_shadow_run_json(service.get_run("shadow-export-1"))

    document = json.loads(payload.decode("utf-8"))
    assert document["policy"]["version"] == "shadow-policy-v1"
    assert document["summary"]["row_count"] == 1
    assert document["rows"][0]["review_state"] == "reviewed"
    assert document["reviews"][0]["action"] == "hold"


def test_csv_export_is_utf8_bom_and_spreadsheet_safe(tmp_path):
    with _saved_run(tmp_path) as service:
        payload = export_shadow_run_csv(service.get_run("shadow-export-1"))

    assert payload.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    assert len(rows) == 1
    assert rows[0]["run_id"] == "shadow-export-1"
    assert rows[0]["llm_reason"] == "'=제외 사유"
    assert rows[0]["review_actions"] == "hold"
