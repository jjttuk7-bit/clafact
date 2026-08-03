"""골든셋 원본 스냅샷 조회 대기열을 점검하거나 실행한다."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clafact.eval.snapshot_query import exclude_completed_requests, limit_requests, period_requests
from clafact.kosis import CachedKosisClient, HttpKosisClient, KosisConnectionError
from clafact.kosis_evidence_snapshot import build_evidence_snapshot
from clafact.kosis_evidence_snapshot_store import KosisEvidenceSnapshotStore


def load_api_key() -> None:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("KOSIS_API_KEY="):
            os.environ.setdefault("KOSIS_API_KEY", line.split("=", 1)[1].strip())
            return


def load_queue(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [item for item in payload["items"] if item["queue_status"] == "ready_for_api_snapshot"]


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E KOSIS 원본 스냅샷 조회 대기열")
    parser.add_argument("--queue", default="reports/e2e_snapshot_query_queue.json")
    parser.add_argument("--execute", action="store_true", help="실제 KOSIS API를 호출해 스냅샷을 저장")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--max-requests", type=int, default=5, help="한 실행에서 처리할 최대 API 요청 수")
    args = parser.parse_args()

    queue = load_queue(ROOT / args.queue)
    all_requests = [
        (item, period, frequency)
        for item in queue
        for period, frequency in period_requests(str(item["기간"]))
    ]
    requests = limit_requests(all_requests, args.max_requests)
    print(json.dumps({"logical_items": len(queue), "total_api_requests": len(all_requests), "scheduled_requests": len(requests)}, ensure_ascii=False))
    if not args.execute:
        for item, period, frequency in requests:
            print(f"대기 {item['candidate_id']} | {item['최종 통계표 ID']} | {period} | {frequency}")
        return 0

    load_api_key()
    client = CachedKosisClient(
        HttpKosisClient(timeout=args.timeout, max_connection_attempts=1),
        cache_dir=ROOT / "data/cache/kosis/e2e_queue",
    )
    saved = failed = 0
    with KosisEvidenceSnapshotStore(ROOT / "data/research/e2e_kosis_snapshots.sqlite") as store:
        completed = set()
        for table_id in {str(item["최종 통계표 ID"]) for item, _, _ in requests}:
            for snapshot in store.list_for_table(table_id):
                params = snapshot.get("query_params", {})
                completed.add((table_id, str(params.get("prd_de", "")), str(params.get("prd_se", ""))))
        pending_keys = set(exclude_completed_requests(
            [(str(item["최종 통계표 ID"]), period, frequency) for item, period, frequency in requests], completed,
        ))
        for item, period, frequency in requests:
            table_id = str(item["최종 통계표 ID"])
            if (table_id, period, frequency) not in pending_keys:
                print(f"건너뜀 {item['candidate_id']} {table_id} {period}: 이미 스냅샷 저장됨")
                continue
            try:
                rows = client.fetch_data("101", table_id, prd_de=period, prd_se=frequency)
            except KosisConnectionError as error:
                failed += 1
                print(f"실패 {item['candidate_id']} {table_id} {period}: {str(error).splitlines()[0]}")
                print("연결 실패 시 같은 배치의 후속 요청은 실행하지 않습니다. 연결 복구 후 다시 실행하세요.")
                break
            snapshot = build_evidence_snapshot(
                org_id="101", table_id=table_id,
                query_params={"prd_de": period, "prd_se": frequency},
                retrieved_at=date.today().isoformat(), rows=rows,
            )
            store.append(snapshot)
            saved += 1
            print(f"저장 {item['candidate_id']} {table_id} {period}: {snapshot.snapshot_id}")
    print(json.dumps({"saved": saved, "failed": failed}, ensure_ascii=False))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
