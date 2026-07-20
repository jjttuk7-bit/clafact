"""실 뉴스 주장 → 실 KOSIS → **실 판정** (파이프라인 전 구간 실데이터 관통).

지금까지: 탐지·분류·검색까지 실데이터로 확인. 이 스크립트는 마지막 구간
(값 조회 → 결정적 판정 → 설명·재현URL)까지 실제로 이어 붙인다.

네트워크 제약: 정부망 접근 가능한 환경(NCP 국내 서버)에서만 동작.
예산: 주장당 검색 1회(같은 지표어는 캐시로 0회) + 값 조회 1회.

사용:
    PYTHONPATH=. python3 scripts/verdict_real.py --limit 5
    PYTHONPATH=. python3 scripts/verdict_real.py --domain prices_inflation --limit 3
"""
from __future__ import annotations

import argparse
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
from clafact.pipeline.retrieve_kosis import KosisSearchIndex  # noqa: E402
from clafact.pipeline.run import verify_sentence  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIED = ROOT.parent / "news_data" / "claims_classified_v01.json"
OUT = ROOT.parent / "news_data" / "verdicts_real.jsonl"

LABEL_KO = {"match": "🟢 일치", "mismatch": "🔴 불일치",
            "unverifiable": "⚪ 판단불가", "not_claim": "— 주장아님"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--domain", default="", help="예: prices_inflation, employment_labor")
    args = ap.parse_args()

    if not os.environ.get("KOSIS_API_KEY"):
        print("KOSIS_API_KEY 없음 — 국내 서버에서 키와 함께 실행하세요.", file=sys.stderr)
        return 1
    if not CLASSIFIED.exists():
        print(f"분류 데이터 없음: {CLASSIFIED}", file=sys.stderr)
        return 1

    recs = json.loads(CLASSIFIED.read_text(encoding="utf-8"))
    cands = [r for r in recs if r.get("source_type", "").startswith("KOSIS")]
    if args.domain:
        cands = [r for r in cands if r.get("domain") == args.domain]
    # 매핑 품질이 좋았던 지표부터 (실측: 소비자물가·취업자·고용률이 우수)
    PREFER = ("소비자물가", "취업자", "고용률", "실업률", "물가상승률")
    cands.sort(key=lambda r: min(
        (i for i, k in enumerate(PREFER) if k in r["sentence"]), default=99))

    client = CachedKosisClient(HttpKosisClient(timeout=30))
    n_by_label: dict[str, int] = {}
    with OUT.open("a", encoding="utf-8") as f:
        for i, c in enumerate(cands[:args.limit], 1):
            sent, date = c["sentence"], c.get("date", "")
            index = KosisSearchIndex(client, period="")
            try:
                r = verify_sentence(sent, date, index, client)
            except Exception as e:  # noqa: BLE001
                print(f"[{i}] ERR {type(e).__name__}: {str(e)[:120]}")
                continue
            n_by_label[r.label] = n_by_label.get(r.label, 0) + 1
            print(f"\n[{i}] {LABEL_KO.get(r.label, r.label)}  (검색어: '{index.last_query}')")
            print(f"    주장: {sent[:90]}")
            print(f"    기사일: {date} | 시점: {r.period} | 수치: {r.quantity}")
            if r.evidence:
                print(f"    근거: {r.evidence.get('tbl')} → {r.evidence.get('value')}")
            if r.calculation:
                print(f"    계산: {r.calculation}")
            print(f"    설명: {(r.explanation or '')[:200]}")
            f.write(json.dumps({
                "sentence": sent, "date": date, "query": index.last_query,
                "label": r.label, "period": r.period, "quantity": r.quantity,
                "evidence": r.evidence, "calculation": r.calculation,
                "reason": r.reason, "explanation": r.explanation,
                "audit": r.audit,
            }, ensure_ascii=False) + "\n")
            f.flush()

    print(f"\n=== 판정 분포: {n_by_label} → {OUT}")
    try:
        print(f"=== 캐시 hit {client.hits} / miss {client.misses} "
              f"| 예산 잔량 {client.inner.budget.remaining()}회")
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
