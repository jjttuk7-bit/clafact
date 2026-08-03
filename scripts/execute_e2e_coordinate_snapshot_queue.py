"""확정된 통계 좌표만 KOSIS에서 수집하는 E2E 스냅샷 실행기."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clafact.eval.snapshot_query import (
    coordinate_query_params, exclude_completed_coordinate_requests, period_requests,
)
from clafact.kosis import HttpKosisClient, KosisConnectionError
from clafact.kosis_evidence_snapshot import build_evidence_snapshot
from clafact.kosis_evidence_snapshot_store import KosisEvidenceSnapshotStore


def main() -> int:
    parser = argparse.ArgumentParser(description="좌표 기반 KOSIS 원본 스냅샷 수집")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-requests", type=int, default=1)
    args = parser.parse_args()
    if args.max_requests < 1:
        raise ValueError("max-requests must be at least 1")
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("KOSIS_API_KEY="):
            os.environ.setdefault("KOSIS_API_KEY", line.split("=", 1)[1].strip())
    queue = json.loads((ROOT / "reports/e2e_snapshot_query_queue.json").read_text(encoding="utf-8"))["items"]
    plans = json.loads((ROOT / "reports/e2e_snapshot_selection_plan.json").read_text(encoding="utf-8"))["plans"]
    plans_by_id = {plan["candidate_id"]: plan for plan in plans}
    requests = []
    for item in queue:
        plan = plans_by_id.get(item["candidate_id"])
        if item.get("queue_status") != "ready_for_api_snapshot" or not plan:
            continue
        for period, frequency in period_requests(str(item["기간"])):
            for params in coordinate_query_params(plan):
                if params:
                    requests.append((item, period, frequency, params))
    completed_params = []
    with KosisEvidenceSnapshotStore(ROOT / "data/research/e2e_kosis_snapshots.sqlite") as store:
        for table_id in {str(item["최종 통계표 ID"]) for item, _, _, _ in requests}:
            completed_params.extend(snapshot.get("query_params", {}) for snapshot in store.list_for_table(table_id))
    request_items = {
        (str(item["최종 통계표 ID"]), period, frequency, tuple(sorted(params.items()))): item
        for item, period, frequency, params in requests
    }
    requests = exclude_completed_coordinate_requests(
        [(str(item["최종 통계표 ID"]), period, frequency, params) for item, period, frequency, params in requests],
        completed_params,
    )
    requests = [
        (request_items[(table_id, period, frequency, tuple(sorted(params.items())))], period, frequency, params)
        for table_id, period, frequency, params in requests
    ]
    requests = requests[:args.max_requests]
    print(json.dumps({"scheduled_coordinate_requests": len(requests)}, ensure_ascii=False))
    if not args.execute:
        for item, period, _, params in requests:
            print(f"대기 {item['candidate_id']} {period} {params}")
        return 0
    client = HttpKosisClient(timeout=20, max_connection_attempts=1)
    with KosisEvidenceSnapshotStore(ROOT / "data/research/e2e_kosis_snapshots.sqlite") as store:
        for item, period, frequency, params in requests:
            query = {"prd_de": period, "prd_se": frequency, **params}
            try:
                rows = client.fetch_data("101", str(item["최종 통계표 ID"]), **query)
            except KosisConnectionError as error:
                print(f"실패 {item['candidate_id']} {period}: {str(error).splitlines()[0]}")
                return 2
            snapshot = build_evidence_snapshot(
                org_id="101", table_id=str(item["최종 통계표 ID"]),
                query_params=query, retrieved_at=date.today().isoformat(), rows=rows,
            )
            store.append(snapshot)
            print(f"저장 {item['candidate_id']} {period} {params}: {snapshot.snapshot_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
