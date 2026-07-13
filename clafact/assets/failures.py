"""A4. 실패 유형 데이터셋 — 실패 레코드 자동 배선.

문서 11 원칙: "실패 1건 = 자산 1줄".
- 파이프라인·평가·리뷰의 실패가 자동으로 레코드가 된다 (수작업 최소화).
- 해결(resolve) 시 파생 자산 ID 가 비어 있으면 거부한다 — 감사 장치.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

STAGES = ("ingest", "detect", "parse", "map", "evidence", "verdict", "explain", "review", "eval")
FAILURE_TYPES = ("detection", "extraction", "mapping", "alignment", "verdict", "explanation")


class FailureRecorder:
    def __init__(self, path: str | Path = "data/failures/failures.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        stage: str,
        ftype: str,
        snapshot: dict,
        cause: str = "",
        run_id: str = "",
    ) -> str:
        """실패 1건 기록. fail_id 반환."""
        if stage not in STAGES:
            raise ValueError(f"stage 는 {STAGES} 중 하나여야 합니다: {stage}")
        if ftype not in FAILURE_TYPES:
            raise ValueError(f"ftype 은 {FAILURE_TYPES} 중 하나여야 합니다: {ftype}")
        fail_id = f"F{time.strftime('%Y%m%d%H%M%S')}-{abs(hash(json.dumps(snapshot, sort_keys=True, ensure_ascii=False))) % 10000:04d}"
        rec = {
            "fail_id": fail_id,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run_id": run_id,
            "stage": stage,
            "type": ftype,
            "snapshot": snapshot,
            "cause": cause,
            "derived_assets": [],
            "resolved": False,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return fail_id

    def resolve(self, fail_id: str, derived_assets: list[str], cause: str = "") -> None:
        """해결 처리. 파생 자산 없이는 해결 불가 — 문서 11 감사 규칙."""
        if not derived_assets:
            raise ValueError(
                "파생 자산 없이 해결 완료 처리할 수 없습니다. "
                "사전(A1)/규칙(A2)/골든셋(A3) 중 무엇을 남겼는지 ID 를 기록하세요."
            )
        rows = self._load()
        found = False
        for r in rows:
            if r["fail_id"] == fail_id:
                r["resolved"] = True
                r["derived_assets"] = derived_assets
                if cause:
                    r["cause"] = cause
                found = True
        if not found:
            raise KeyError(f"fail_id 없음: {fail_id}")
        with self.path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def stats(self) -> dict:
        """주간 회고(WF-4)용 집계: 유형별 분포·해결률·자산 전환율."""
        rows = self._load()
        by_type: dict[str, int] = {}
        resolved = 0
        with_assets = 0
        for r in rows:
            by_type[r["type"]] = by_type.get(r["type"], 0) + 1
            if r["resolved"]:
                resolved += 1
                if r["derived_assets"]:
                    with_assets += 1
        return {
            "total": len(rows),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "resolved": resolved,
            "asset_conversion_rate": (with_assets / resolved) if resolved else None,
        }

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
