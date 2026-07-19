"""ClaFact 서비스 v0 CLI — 한 명령으로 도는 배치 서비스 (문서 25 S0).

사용:
  python scripts/service_run.py ingest --input data/samples/articles.jsonl
  python scripts/service_run.py process [--limit 100]
  python scripts/service_run.py queue      # 리뷰 큐 (위험한 것부터)
  python scripts/service_run.py review --claim clm_xxx --action approve|correct|reject
  python scripts/service_run.py report

엔진 스위치: 지금은 Fixture(오프라인). 실서비스 전환은 아래 두 줄 교체 —
  StatIndex(실 인덱스) + CachedKosisClient(HttpKosisClient())
단, 개발망은 정부망 443 차단이므로 실 API 는 클라우드에서만 (구현계획 §준비 게이트).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clafact.kosis import FixtureKosisClient           # noqa: E402
from clafact.pipeline.retrieve import StatIndex        # noqa: E402
from clafact.service import batch, store as st        # noqa: E402
from clafact.service.store import Store               # noqa: E402

DEFAULT_DB = ROOT / "data" / "service" / "clafact.db"


def _engine():
    return (StatIndex(ROOT / "data/samples/kosis/tables_meta.json"),
            FixtureKosisClient(ROOT / "data/samples/kosis"))


def main() -> int:
    p = argparse.ArgumentParser(description="ClaFact service v0")
    p.add_argument("command", choices=["ingest", "process", "queue", "review", "report"])
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--input", help="ingest: 기사 파일 (jsonl/csv)")
    p.add_argument("--limit", type=int, default=None, help="process: 최대 처리 건수")
    p.add_argument("--claim", help="review: 대상 claim_id")
    p.add_argument("--action", choices=["approve", "correct", "reject"])
    p.add_argument("--note", default="", help="review: 보정·반려 사유")
    args = p.parse_args()

    store = Store(args.db)
    try:
        if args.command == "ingest":
            if not args.input:
                p.error("ingest 에는 --input 이 필요합니다")
            out = batch.ingest_file(store, args.input)
        elif args.command == "process":
            idx, client = _engine()
            out = batch.process_pending(store, idx, client, limit=args.limit)
        elif args.command == "queue":
            rows = store.review_queue()
            out = [{"claim_id": r["claim_id"], "label": r["label"],
                    "confidence": r["confidence"], "sentence": r["sentence"][:60]}
                   for r in rows]
        elif args.command == "review":
            if not (args.claim and args.action):
                p.error("review 에는 --claim 과 --action 이 필요합니다")
            store.apply_review(args.claim, args.action, note=args.note)
            out = {"claim_id": args.claim, "action": args.action, "ok": True}
        else:  # report
            out = store.summary()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
