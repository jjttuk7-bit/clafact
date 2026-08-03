"""KOSIS 통계목록을 제한된 호출 단위로 수집·재개한다."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clafact.kosis import HttpKosisClient, KosisConnectionError
from clafact.kosis_catalog import crawl_catalog, save_catalog_snapshot


def load_api_key() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("KOSIS_API_KEY="):
            os.environ.setdefault("KOSIS_API_KEY", line.split("=", 1)[1].strip())
            return


def state_from_snapshot(path: Path) -> tuple[list[str], list[str]]:
    if not path.exists():
        return [""], []
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [""], []
    return snapshot.get("pending_parent_ids") or [""], snapshot.get("seen_parent_ids") or []


def main() -> int:
    parser = argparse.ArgumentParser(description="KOSIS 통계목록 증분 수집")
    parser.add_argument("--view", default="MT_ZTITLE")
    parser.add_argument("--snapshot", default="data/catalog/kosis_mt_ztitled.json")
    parser.add_argument("--max-list-calls", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    load_api_key()
    snapshot = ROOT / args.snapshot
    pending, seen = state_from_snapshot(snapshot)
    client = HttpKosisClient(timeout=args.timeout, max_connection_attempts=1)
    crawl = crawl_catalog(client, args.view, pending, max_list_calls=args.max_list_calls,
                          seen_parent_ids=seen)
    saved = save_catalog_snapshot(snapshot, args.view, crawl)
    print(json.dumps({"saved": saved, "list_calls": crawl["list_calls"]}, ensure_ascii=False))
    if crawl.get("connection_error"):
        print(f"KOSIS 연결 실패 — 성공한 결과는 저장했고 다음 노드부터 재개합니다.\n{crawl['connection_error']}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
