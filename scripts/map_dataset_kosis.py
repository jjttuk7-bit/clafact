"""데이터셋 전수 → KOSIS 매핑 배치 (예산 인지형).

전략(순진한 건별 호출 금지):
  1. 소스분류로 KOSIS 후보만 남긴다 (16,464 → ~820, 95% 예산 낭비 차단)
  2. 질의를 생성하고 **중복 제거** (실업률 기사 수십 건 → 통계표 검색 1회)
  3. 예산(개발계정 1,000회) 안에서만 실행 — 초과분은 다음 실행으로 이월(캐시 resumable)

네트워크 제약: 개발망은 정부망 443 차단 → 실행(--execute)은 **클라우드에서만** 동작.
로컬에서는 --dry-run 으로 예산 소요만 계산(호출 0회).

사용:
  # 로컬: 예산 추정만 (네트워크·키 불필요)
  PYTHONPATH=. python scripts/map_dataset_kosis.py --dry-run

  # 클라우드: 실 매핑 (KOSIS_API_KEY 필요, 예산 가드 자동)
  PYTHONPATH=. python scripts/map_dataset_kosis.py --execute --limit 300
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clafact.assets.alias_dict import AliasDict
from clafact.pipeline import source_classify as sc
from clafact.pipeline.query_gen import make_query

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIED = ROOT.parent / "news_data" / "claims_classified_v01.json"
OUT_DIR = ROOT.parent / "news_data"


def load_kosis_candidates() -> list[dict]:
    """분류 결과에서 KOSIS 후보(DOMESTIC+COMPLEX)만 — 분류 JSON 있으면 재사용,
    없으면 원본 CSV에서 즉석 분류."""
    if CLASSIFIED.exists():
        recs = json.loads(CLASSIFIED.read_text(encoding="utf-8"))
        return [r for r in recs if r.get("source_type", "").startswith("KOSIS")]
    # 폴백: CSV에서 즉석 (source_classify 재적용)
    from clafact.pipeline.ingest import load_articles
    from clafact.pipeline.detect import filter_sentences
    csv = OUT_DIR / "[AI 기반 뉴스 사실검증 시스템] 프로젝트 데이터.csv"
    out = []
    for a in load_articles(csv):
        for _, s in filter_sentences(a.sentences):
            lbl = sc.classify(s)
            if lbl.source_type.startswith("KOSIS"):
                out.append({"sentence": s, "date": a.date,
                            "source_type": lbl.source_type, "domain": lbl.domain})
    return out


def build_plan(cands: list[dict]) -> dict:
    """질의 생성 + 중복 제거 → 실행 계획(고유 질의별 소속 Claim 목록).

    KOSIS 통합검색은 짧은 지표어를 기대하므로 `kosis_query`(매칭 지표어)를 쓴다.
    긴 문장형 질의(make_query)는 실측에서 27/30이 err30으로 실패했다.
    부수 효과: 지표어 단위라 중복 제거율이 급등한다(820건 → 지표어 수십 개).
    """
    q_to_claims: dict[str, list[dict]] = defaultdict(list)
    for c in cands:
        q = sc.kosis_query(c["sentence"])
        if not q:                     # 지표어를 못 찾으면 검색 자체를 시도하지 않는다
            continue                  # (예산 낭비 방지 — 쓰레기 질의 컷)
        q_to_claims[q].append(c)
    return q_to_claims


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="예산 추정만 (호출 0)")
    ap.add_argument("--execute", action="store_true", help="실 KOSIS 검색 (클라우드·키 필요)")
    ap.add_argument("--limit", type=int, default=0, help="이번 실행 최대 검색 수 (예산 방어)")
    ap.add_argument("--top-k", type=int, default=10)
    args = ap.parse_args()
    if not (args.dry_run or args.execute):
        args.dry_run = True

    cands = load_kosis_candidates()
    plan = build_plan(cands)
    uniq = sorted(plan, key=lambda q: -len(plan[q]))

    print(f"KOSIS 후보 Claim: {len(cands):,}")
    print(f"고유 검색어(중복 제거 후): {len(uniq):,}  ← 실제 필요한 검색 호출 수")
    dom = Counter(c["domain"] for c in cands)
    print(f"도메인 분포: {dict(dom)}")
    print(f"검색어당 평균 Claim: {len(cands)/max(len(uniq),1):.1f}  (중복 제거가 아낀 배수)")
    print("\n상위 검색어 15 (많은 Claim이 붙은 = 우선 매핑 가치 높음):")
    for q in uniq[:15]:
        print(f"  [{len(plan[q]):3}건] {q[:60]}")

    if args.dry_run:
        # 예산 추정: 검색 1회/고유질의 (+ 나중에 값조회는 매핑 성공분만)
        try:
            from clafact.throttle import CallBudget
            remaining = CallBudget().remaining()
        except Exception:
            remaining = 999
        need = len(uniq)
        print(f"\n=== 예산 추정 ===")
        print(f"검색 호출 필요: {need:,}회 (고유 질의 1회씩)")
        print(f"현재 예산 잔량: {remaining:,}회")
        if need <= remaining:
            print(f"✅ 단일 실행 가능 (검색 후 잔량 {remaining-need:,}회 → 값 조회에 사용)")
        else:
            batches = -(-need // max(remaining, 1))
            print(f"⚠️ 예산 초과 — {batches}회 분할 실행 필요 (또는 상위 질의만 --limit {remaining})")
        # 계획 파일 저장 (실행 시 resumable 하게 이 순서로)
        plan_path = OUT_DIR / "kosis_mapping_plan.json"
        plan_path.write_text(json.dumps(
            [{"query": q, "n_claims": len(plan[q]),
              "domain": Counter(c["domain"] for c in plan[q]).most_common(1)[0][0]}
             for q in uniq], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n계획 저장: {plan_path} (실행 시 이 순서로 검색)")
        return 0

    # --execute: 실 검색 (클라우드)
    import os
    if not os.environ.get("KOSIS_API_KEY"):
        print("KOSIS_API_KEY 없음 — 클라우드에서 키와 함께 실행하세요.", file=sys.stderr)
        return 1
    from clafact.kosis import HttpKosisClient, CachedKosisClient
    from clafact.pipeline.retrieve_kosis import search_kosis
    client = CachedKosisClient(HttpKosisClient())
    out_path = OUT_DIR / "kosis_mapping_results.jsonl"
    done = errors = 0
    limit = args.limit or len(uniq)
    # 질의 하나의 실패가 배치 전체를 죽이면 안 된다 — 기록하고 계속한다.
    # 오직 예산 소진일 때만 중단(더 돌려봐야 전부 실패이므로).
    BUDGET_SIGNS = ("예산", "한도", "budget", "quota")
    with out_path.open("a", encoding="utf-8") as f:
        for i, q in enumerate(uniq[:limit], 1):
            try:
                hits = search_kosis(q, client, top_k=args.top_k)
                rec = {"query": q, "n_claims": len(plan[q]),
                       "hits": [{"org_id": h.org_id, "tbl_id": h.tbl_id,
                                 "tbl_name": h.tbl_name, "score": h.score} for h in hits[:5]]}
                print(f"[{i}/{limit}] hit {len(hits)}건 ← {q[:40]}")
            except Exception as e:  # noqa: BLE001
                msg = f"{type(e).__name__}: {e}"
                if any(s in msg for s in BUDGET_SIGNS):
                    print(f"예산 소진으로 중단: {msg[:160]}")
                    break
                rec = {"query": q, "n_claims": len(plan[q]), "hits": [],
                       "error": msg[:200]}
                errors += 1
                print(f"[{i}/{limit}] ERR {msg[:90]} ← {q[:30]}")
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()          # 중간에 끊겨도 여기까지는 남는다
            done += 1
    print(f"\n검색 완료: {done}건 (에러 {errors}건) → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
