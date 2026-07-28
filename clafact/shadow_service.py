"""Shadow Lab UI와 연구 구성 요소 사이의 안정된 서비스 경계."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from clafact.experiment_types import Judge
from clafact.shadow_policy import ShadowPolicy
from clafact.shadow_runner import run_shadow_experiment
from clafact.shadow_store import ShadowStore


class ShadowLabService:
    """연구 실행·저장·조회·검토를 제공하며 운영 저장소에는 접근하지 않는다."""

    def __init__(self, database_path: str | Path) -> None:
        self.store = ShadowStore(database_path)

    def execute(
        self,
        text: str,
        article_date: str,
        policy: ShadowPolicy,
        *,
        judge_fn: Judge | None = None,
        run_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        experiment = run_shadow_experiment(text, article_date, policy, judge_fn=judge_fn)
        resolved_run_id = run_id or f"shadow-{uuid4().hex}"
        resolved_created_at = created_at or datetime.now(timezone.utc).isoformat()
        input_hash = sha256(f"{article_date}\n{text}".encode("utf-8")).hexdigest()
        summary = {
            "row_count": len(experiment.rows),
            "review_count": sum(row["review_state"] == "needs_review" for row in experiment.rows),
            "llm_calls": experiment.llm_calls,
            "elapsed_ms": experiment.elapsed_ms,
            "disagreement_counts": experiment.disagreement_counts,
        }
        run = {
            "run_id": resolved_run_id,
            "created_at": resolved_created_at,
            "input_hash": input_hash,
            "policy_json": json.dumps(policy.as_dict(), ensure_ascii=False, sort_keys=True),
            "baseline_name": "existing-python-rules",
            "shadow_name": "python-llm-hybrid-comparison",
            "status": "completed",
            "summary_json": json.dumps(summary, ensure_ascii=False, sort_keys=True),
        }
        stored_rows = [
            {
                "run_id": resolved_run_id,
                "row_index": row["row_index"],
                "sentence": row["sentence"],
                "baseline_json": json.dumps(row["baseline"], ensure_ascii=False, sort_keys=True),
                "shadow_json": json.dumps(row["shadow"], ensure_ascii=False, sort_keys=True),
                "review_state": row["review_state"],
                "risk_reasons_json": json.dumps(row["risk_reasons"], ensure_ascii=False),
            }
            for row in experiment.rows
        ]
        inserted = self.store.append_run(run, stored_rows)
        return {"run_id": resolved_run_id, "inserted": inserted, "summary": summary}

    def list_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return [
            {
                "run_id": run["run_id"],
                "created_at": run["created_at"],
                "policy": json.loads(run["policy_json"]),
                "status": run["status"],
                "summary": json.loads(run["summary_json"]),
            }
            for run in self.store.list_runs(limit=limit)
        ]
    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self.store.get_run(run_id)
        if run is None:
            return None
        return {
            "run_id": run["run_id"],
            "created_at": run["created_at"],
            "input_hash": run["input_hash"],
            "policy": json.loads(run["policy_json"]),
            "baseline_name": run["baseline_name"],
            "shadow_name": run["shadow_name"],
            "status": run["status"],
            "summary": json.loads(run["summary_json"]),
            "rows": [self._decode_row(row) for row in self.store.list_rows(run_id)],
            "reviews": self.store.list_reviews(run_id),
        }

    def list_review_rows(self, run_id: str) -> list[dict[str, Any]]:
        return [self._decode_row(row) for row in self.store.list_review_rows(run_id)]

    def review(
        self, run_id: str, row_index: int, *, action: str, note: str, reviewed_at: str
    ) -> bool:
        return self.store.append_review(
            run_id, row_index, action=action, note=note, reviewed_at=reviewed_at
        )

    @staticmethod
    def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": row["run_id"],
            "row_index": row["row_index"],
            "sentence": row["sentence"],
            "baseline": json.loads(row["baseline_json"]),
            "shadow": json.loads(row["shadow_json"]),
            "review_state": row["review_state"],
            "risk_reasons": json.loads(row["risk_reasons_json"]),
        }

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "ShadowLabService":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
