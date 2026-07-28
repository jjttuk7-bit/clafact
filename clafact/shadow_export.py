"""Shadow Lab 연구 결과의 휴대 가능한 JSON·CSV 내보내기."""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Mapping


SHADOW_CSV_COLUMNS = (
    "run_id", "created_at", "input_hash", "policy_version", "baseline_name", "shadow_name",
    "status", "row_index", "sentence", "python_candidate", "llm_candidate", "hybrid_candidate",
    "llm_reason", "hcx_status", "disagreement_class", "claim_type", "route", "quantities",
    "parsed_period", "risk_reasons", "review_state", "review_actions", "review_notes",
    "kosis_table_id", "kosis_evidence_object_id", "kosis_mapping_status",
    "kosis_match_score", "kosis_match_reasons", "kosis_score_breakdown", "kosis_source_selection", "kosis_mapping_note",
)


def _spreadsheet_safe(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    if re.match(r"^[\s\x00-\x1f]*[=+\-@]", value) or value[0] in {"\t", "\r", "\n"}:
        return "'" + value
    return value


def group_kosis_mappings_by_row(
    mappings: list[Mapping[str, Any]],
) -> dict[int, list[Mapping[str, Any]]]:
    """Group persisted KOSIS mappings by Shadow sentence row."""
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for mapping in mappings:
        grouped.setdefault(int(mapping["row_index"]), []).append(mapping)
    return grouped

def _flatten_kosis_mappings(mappings: list[Mapping[str, Any]]) -> dict[str, str]:
    """Return spreadsheet cells for zero or more research-only KOSIS mappings."""

    def values(key: str) -> list[str]:
        return [str(mapping.get(key, "") or "") for mapping in mappings]

    def reasons(mapping: Mapping[str, Any]) -> str:
        return " | ".join(str(reason) for reason in mapping.get("match_reasons", ()))

    def score_breakdown(mapping: Mapping[str, Any]) -> str:
        return " ; ".join(str(item) for item in mapping.get("match_score_breakdown", ()))

    def selection(mapping: Mapping[str, Any]) -> str:
        return "; ".join(
            f"{key}={value}" for key, value in mapping.get("source_selection", {}).items()
        )

    table_ids = values("table_id")
    evidence_ids = [str(mapping.get("evidence_id") or mapping.get("table_id", "")) for mapping in mappings]
    return {
        "kosis_table_id": " | ".join(table_ids),
        "kosis_evidence_object_id": " | ".join(evidence_ids),
        "kosis_mapping_status": " | ".join(values("status")),
        "kosis_match_score": " | ".join(values("match_score")),
        "kosis_match_reasons": " | ".join(reasons(mapping) for mapping in mappings),
        "kosis_score_breakdown": " | ".join(score_breakdown(mapping) for mapping in mappings),
        "kosis_source_selection": " | ".join(selection(mapping) for mapping in mappings),
        "kosis_mapping_note": " | ".join(values("note")),
    }


def export_shadow_run_json(run: Mapping[str, Any] | None) -> bytes:
    """내보내기 시점의 완전한 Shadow 실행 스냅샷을 UTF-8 JSON으로 반환한다."""
    if run is None:
        raise KeyError("Shadow 실행을 찾을 수 없습니다")
    return json.dumps(run, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def export_shadow_run_csv(
    run: Mapping[str, Any] | None, *,
    mappings_by_row: Mapping[int, list[Mapping[str, Any]]] | None = None,
) -> bytes:
    """행 단위 분석용, Excel 안전 UTF-8 BOM CSV를 반환한다."""
    if run is None:
        raise KeyError("Shadow 실행을 찾을 수 없습니다")
    mappings_by_row = mappings_by_row or {}
    reviews_by_row: dict[int, list[dict[str, Any]]] = {}
    for review in run.get("reviews", []):
        reviews_by_row.setdefault(int(review["row_index"]), []).append(review)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=SHADOW_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in run["rows"]:
        shadow = row["shadow"]
        reviews = reviews_by_row.get(int(row["row_index"]), [])
        flattened = _flatten_kosis_mappings(mappings_by_row.get(int(row["row_index"]), []))
        flattened.update({
            "run_id": run["run_id"],
            "created_at": run["created_at"],
            "input_hash": run["input_hash"],
            "policy_version": run["policy"].get("version", ""),
            "baseline_name": run["baseline_name"],
            "shadow_name": run["shadow_name"],
            "status": run["status"],
            "row_index": row["row_index"],
            "sentence": row["sentence"],
            "python_candidate": row["baseline"].get("python_candidate"),
            "llm_candidate": shadow.get("llm_candidate"),
            "hybrid_candidate": shadow.get("hybrid_candidate"),
            "llm_reason": shadow.get("llm_reason", ""),
            "hcx_status": shadow.get("hcx_status", ""),
            "disagreement_class": shadow.get("disagreement_class", ""),
            "claim_type": shadow.get("claim_type", ""),
            "route": shadow.get("route", ""),
            "quantities": " | ".join(shadow.get("quantities", [])),
            "parsed_period": shadow.get("parsed_period", ""),
            "risk_reasons": " | ".join(row.get("risk_reasons", [])),
            "review_state": row["review_state"],
            "review_actions": " | ".join(review["action"] for review in reviews),
            "review_notes": " | ".join(review["note"] for review in reviews),
        })
        writer.writerow({key: _spreadsheet_safe(value) for key, value in flattened.items()})
    return output.getvalue().encode("utf-8-sig")
