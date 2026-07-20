"""통합검색 원본 응답 필드 진단 — 리랭킹 설계용.

후보 표를 재순위하려면 어떤 메타(주기·지역·수록기간)가 오는지 알아야 한다.
캐시된 질의는 예산 0원으로 조회된다(CachedKosisClient).

사용:
    PYTHONPATH=. python3 scripts/inspect_search.py 소비자물가
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clafact.kosis import CachedKosisClient, HttpKosisClient  # noqa: E402


def main() -> int:
    query = sys.argv[1] if len(sys.argv) > 1 else "소비자물가"
    if not os.environ.get("KOSIS_API_KEY"):
        print("KOSIS_API_KEY 없음", file=sys.stderr)
        return 1
    client = CachedKosisClient(HttpKosisClient(timeout=30))
    rows = client.integrated_search(searchNm=query, sort="RANK", resultCount=10)
    print(f"질의 '{query}' → {len(rows)}건 "
          f"(캐시 hit {client.hits} / miss {client.misses} — miss 0이면 예산 0원)\n")
    if rows:
        print("=== 사용 가능한 필드(첫 행 키) ===")
        print(", ".join(sorted(rows[0].keys())))
        print("\n=== 후보 10개 상세 ===")
        for i, r in enumerate(rows, 1):
            print(f"\n[{i}] {r.get('TBL_NM', '')}")
            print(f"    TBL_ID={r.get('TBL_ID')} ORG_ID={r.get('ORG_ID')} "
                  f"STAT_NM={r.get('STAT_NM', '')}")
            # 리랭킹 후보 신호가 될 만한 필드를 전부 노출
            extra = {k: v for k, v in r.items()
                     if k not in ("TBL_NM", "TBL_ID", "ORG_ID", "STAT_NM")}
            print(f"    {json.dumps(extra, ensure_ascii=False)[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
