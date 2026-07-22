"""Presentation helpers for the Streamlit operations dashboard."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


_STATUS_LABELS = {
    "PENDING": "● 대기",
    "PROCESSING": "◌ 처리 중",
    "COMPLETED": "✓ 처리 완료",
    "FAILED": "! 처리 실패",
}

_HCX_LABELS = {"live": "실시간 보조", "fixture": "테스트 모드"}


def build_ops_claim_rows(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Map stored claims into readable, presentation-ready audit rows."""
    rows = []
    for claim in claims:
        try:
            audit = json.loads(claim.get("audit_json") or "{}")
        except json.JSONDecodeError:
            audit = {}
        hcx = audit.get("hcx_detection", {})
        mode = hcx.get("mode")
        rows.append({
            "주장": claim.get("sentence") or "-",
            "처리 상태": _STATUS_LABELS.get(claim.get("status"), claim.get("status") or "상태 없음"),
            "판정": claim.get("label") or "판정 전",
            "등급": claim.get("tier") or "-",
            "HCX 신호": _HCX_LABELS.get(mode, hcx.get("fallback") or "규칙 기반"),
            "오류": claim.get("error") or "-",
        })
    return rows
