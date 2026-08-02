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
    assert document["rows"][0]["review_state"] == "hold"
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


def test_csv_export_merges_multiple_kosis_mappings_per_sentence(tmp_path):
    mappings_by_row = {
        1: [
            {
                "table_id": "DT_CPI_MONTH",
                "status": "reviewed",
                "match_score": 92,
                "match_reasons": ["지표 일치", "단위 일치"],
                "source_selection": {"시점": "2025.10", "품목": "총지수"},
                "note": "기사 수치 직접 확인",
            },
            {
                "table_id": "DT_CPI_REFERENCE",
                "status": "candidate",
                "match_score": None,
                "match_reasons": [],
        "match_score_breakdown": ["+40 지표 의미 일치 (전년동월비)", "+25 단위 일치 (%)"],
                "source_selection": {},
                "note": "보조 근거",
            },
        ]
    }
    with _saved_run(tmp_path) as service:
        payload = export_shadow_run_csv(
            service.get_run("shadow-export-1"), mappings_by_row=mappings_by_row
        )

    row = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))[0]
    assert row["kosis_table_id"] == "DT_CPI_MONTH | DT_CPI_REFERENCE"
    assert row["kosis_evidence_object_id"] == "DT_CPI_MONTH | DT_CPI_REFERENCE"
    assert row["kosis_mapping_status"] == "reviewed | candidate"
    assert row["kosis_match_score"] == "92 | "
    assert row["kosis_match_reasons"] == "지표 일치 | 단위 일치 | "
    assert row["kosis_source_selection"] == "시점=2025.10; 품목=총지수 | "
    assert row["kosis_mapping_note"] == "기사 수치 직접 확인 | 보조 근거"


def test_group_kosis_mappings_by_row_keeps_all_links_in_sentence_order():
    from clafact.shadow_export import group_kosis_mappings_by_row

    grouped = group_kosis_mappings_by_row([
        {"row_index": 2, "table_id": "DT_SECOND"},
        {"row_index": 1, "table_id": "DT_FIRST"},
        {"row_index": 2, "table_id": "DT_SUPPORT"},
    ])

    assert [mapping["table_id"] for mapping in grouped[1]] == ["DT_FIRST"]
    assert [mapping["table_id"] for mapping in grouped[2]] == ["DT_SECOND", "DT_SUPPORT"]


def test_csv_export_uses_exact_kosis_evidence_object_id(tmp_path):
    mappings_by_row = {1: [{
        "table_id": "DT_1J22042",
        "evidence_id": "DT_1J22042:year-over-year",
        "status": "reviewed",
        "match_score": 95,
        "match_reasons": [],
        "match_score_breakdown": ["+40 지표 의미 일치 (전년동월비)", "+25 단위 일치 (%)"],
        "source_selection": {"지수종류": "총지수"},
        "note": "전년동월비",
    }]}
    with _saved_run(tmp_path) as service:
        payload = export_shadow_run_csv(
            service.get_run("shadow-export-1"), mappings_by_row=mappings_by_row
        )

    row = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))[0]
    assert row["kosis_table_id"] == "DT_1J22042"
    assert row["kosis_evidence_object_id"] == "DT_1J22042:year-over-year"
    assert row["kosis_score_breakdown"] == "'+40 지표 의미 일치 (전년동월비) ; +25 단위 일치 (%)"


def test_csv_export_includes_actual_kosis_value_comparison(tmp_path):
    comparisons_by_row = {1: [{
        "status": "match", "reason": "값 일치", "claim_value": "2.4%",
        "official_value": "2.4%", "claim_period": "2025-10",
        "snapshot_id": "kosis-snapshot-1",
        "gate_results": [{"name": "기간", "passed": True, "detail": "2025-10 일치"}],
    }]}
    with _saved_run(tmp_path) as service:
        payload = export_shadow_run_csv(
            service.get_run("shadow-export-1"), comparisons_by_row=comparisons_by_row
        )

    row = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))[0]
    assert row["kosis_value_comparison_status"] == "match"
    assert row["kosis_claim_value"] == "2.4%"
    assert row["kosis_snapshot_id"] == "kosis-snapshot-1"
    assert row["kosis_value_comparison_gates"] == "기간: 통과(2025-10 일치)"

def test_csv_export_includes_completed_claim_verdict_and_reproducible_evidence(tmp_path):
    completed_claims_by_row = {1: [{
        "verdict": "mismatch",
        "snapshot_id": "kosis-completed-1",
        "evidence_id": "DT_CPI_MONTH:total",
        "evidence": {
            "table_id": "DT_CPI_MONTH",
            "source_url": "https://kosis.kr/reproducible",
        },
    }]}
    with _saved_run(tmp_path) as service:
        payload = export_shadow_run_csv(
            service.get_run("shadow-export-1"),
            completed_claims_by_row=completed_claims_by_row,
        )

    row = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))[0]
    assert row["claim_completion_verdict"] == "mismatch"
    assert row["claim_completion_snapshot_id"] == "kosis-completed-1"
    assert row["claim_completion_table_id"] == "DT_CPI_MONTH"
    assert row["claim_completion_reproducible_url"] == "https://kosis.kr/reproducible"