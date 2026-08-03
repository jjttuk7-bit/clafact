"""E2E 골든셋의 확정 KOSIS 근거를 원본 API 스냅샷으로 저장한다."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clafact.kosis import CachedKosisClient, HttpKosisClient, KosisConnectionError
from clafact.kosis_evidence_snapshot import build_evidence_snapshot
from clafact.kosis_evidence_snapshot_store import KosisEvidenceSnapshotStore

REQUESTS = (
    ("DT_1J22003", "2025-05"),
    ("DT_1J22042", "2025-05"),
    ("DT_1J22042", "2025-02"),
    ("DT_1J22042", "2025-10"),
)


def load_api_key() -> None:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("KOSIS_API_KEY="):
            os.environ.setdefault("KOSIS_API_KEY", line.split("=", 1)[1].strip())
            return


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E KOSIS 원본 근거 스냅샷 수집")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    load_api_key()
    client = CachedKosisClient(
        HttpKosisClient(timeout=args.timeout, max_connection_attempts=1),
        cache_dir=ROOT / "data/cache/kosis/e2e_evidence",
    )
    success = error = 0
    with KosisEvidenceSnapshotStore(ROOT / "data/research/e2e_kosis_snapshots.sqlite") as store:
        for table_id, period in REQUESTS:
            try:
                rows = client.fetch_data("101", table_id, prd_de=period, prd_se="M")
            except KosisConnectionError as exc:
                error += 1
                print(f"실패 {table_id} {period}: {str(exc).splitlines()[0]}")
                continue
            snapshot = build_evidence_snapshot(
                org_id="101", table_id=table_id,
                query_params={"prd_de": period, "prd_se": "M"},
                retrieved_at="2026-08-02", rows=rows,
            )
            store.append(snapshot)
            success += 1
            print(f"저장 {table_id} {period}: {len(rows)}행 {snapshot.snapshot_id}")
    print(f"완료 성공={success} 실패={error} 캐시={client.stats()}")
    return 0 if not error else 2


if __name__ == "__main__":
    raise SystemExit(main())
