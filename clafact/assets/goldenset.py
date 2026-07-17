"""A3. 골든셋 — 평가 기준 데이터의 append 경로.

문서 11 원칙: "리뷰에서 뒤집히면 골든셋에 추가한다. 예외 없이."

플라이휠에서 이 모듈의 역할이 결정적이다.
관객이(혹은 검증자가) 시스템을 속인 문장은 골든셋에 없으므로,
추가하지 않으면 재평가가 반응하지 않는다 —
**추가해야 점수가 (일단) 떨어지고, 그 하락이 골든셋이 진짜라는 증거다.**
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LABELS = ("match", "mismatch", "unverifiable")
CLAIM_TYPES = ("increase_decrease", "scale", "comparison", "forecast", None)


def load(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def next_article_id(path: str | Path) -> str:
    """마지막 A0NN + 1."""
    nums = [0]
    for r in load(path):
        m = re.match(r"A(\d+)$", str(r.get("article_id", "")))
        if m:
            nums.append(int(m.group(1)))
    return f"A{max(nums) + 1:03d}"


def append_row(
    path: str | Path,
    sentence: str,
    is_claim: bool,
    gold_label: str | None = None,
    claim_type: str | None = None,
    claimed_value: float | None = None,
    claimed_unit: str = "",
    evidence_value: float | None = None,
    evidence_unit: str = "",
    notes: str = "",
) -> dict:
    """골든셋 1행 추가. 저장된 행(dict) 반환."""
    sentence = sentence.strip()
    if not sentence:
        raise ValueError("sentence 는 비울 수 없습니다.")
    if gold_label is not None and gold_label not in LABELS:
        raise ValueError(f"gold_label 은 {LABELS} 중 하나여야 합니다: {gold_label}")
    if is_claim and gold_label is None:
        raise ValueError("is_claim=True 인 행은 gold_label 이 필요합니다 (판정 평가 대상).")

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if any(r.get("sentence", "").strip() == sentence for r in load(p)):
        raise ValueError("이미 골든셋에 있는 문장입니다.")

    row = {
        "article_id": next_article_id(p),
        "sentence_id": "s1",
        "sentence": sentence,
        "is_claim": bool(is_claim),
        "claim_type": claim_type,
        "gold_label": gold_label,
        "claimed_value": claimed_value,
        "claimed_unit": claimed_unit,
        "evidence_value": evidence_value,
        "evidence_unit": evidence_unit,
        "notes": notes,
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def stats(path: str | Path) -> dict:
    rows = load(path)
    by_label: dict[str, int] = {}
    for r in rows:
        k = r.get("gold_label") or "not_claim"
        by_label[k] = by_label.get(k, 0) + 1
    return {"total": len(rows), "by_label": dict(sorted(by_label.items(), key=lambda x: -x[1]))}
