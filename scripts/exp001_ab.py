"""EXP-001 — 매핑 경로 A/B/하이브리드 비교 실험 (문서 12 §4).

가설: 임베딩 의미 검색(경로 B)이 키워드 검색(경로 A)의 함정 케이스
      ('일자리 못 구한 사람' → 실업률)를 개선한다.
평가: 매핑 평가셋의 gold_tbl_id 기준 Hit@1 / Hit@3 / MRR.

⚠️ 지금 경로 B 는 문자 n-gram 프록시다. 이 실험의 진짜 산출물은 점수가 아니라
   "각 경로가 어떤 유형에서 이기고 지는가"의 정보 — 진짜 임베딩(HCX) 도입의 근거.

사용법: python scripts/exp001_ab.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clafact.assets.alias_dict import AliasDict
from clafact.pipeline.retrieve import StatIndex
from clafact.pipeline.retrieve_semantic import SemanticIndex

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/samples/kosis/tables_meta.json"
EVAL = ROOT / "data/goldenset/mapping_eval.jsonl"

tables = json.loads(META.read_text(encoding="utf-8"))
cases = [json.loads(l) for l in EVAL.read_text(encoding="utf-8").strip().splitlines()]

empty_alias = AliasDict(ROOT / "data/assets/_none.jsonl")   # 파일 없음 → 빈 사전
real_alias = AliasDict(ROOT / "data/assets/aliases.jsonl")

idx_kw = StatIndex(META, aliases=empty_alias)   # 경로 A: 키워드만
idx_al = StatIndex(META, aliases=real_alias)    # 경로 A+별칭
sem = SemanticIndex(tables, aliases=real_alias)  # 경로 B (+하이브리드 옵션)


def ranks(hits, k=3):
    """StatIndex(TableHit) 와 SemanticIndex(tuple) 반환형을 통일."""
    out = []
    for h in hits[:k]:
        out.append(h.tbl_id if hasattr(h, "tbl_id") else h[0])
    return out


def rrf(rank_lists, k_const=60, top_k=3):
    """Reciprocal Rank Fusion — 여러 랭킹을 순위 기반으로 융합."""
    score = {}
    for rl in rank_lists:
        for rank, tid in enumerate(rl):
            score[tid] = score.get(tid, 0.0) + 1.0 / (k_const + rank + 1)
    return [t for t, _ in sorted(score.items(), key=lambda x: -x[1])][:top_k]


PATHS = {
    "A. 키워드만":      lambda q: ranks(idx_kw.search(q)),
    "A+별칭":          lambda q: ranks(idx_al.search(q)),
    "B. 의미(n-gram)":  lambda q: ranks(sem.search(q)),
    "하이브리드(A+별칭+B)": lambda q: rrf([ranks(idx_al.search(q, 5)), ranks(sem.search(q, 5))]),
}


def evaluate():
    agg = {name: {"h1": 0, "h3": 0, "mrr": 0.0} for name in PATHS}
    per_case = []
    for c in cases:
        gold = c["gold_tbl_id"]
        row = {"query": c["query"][:26], "gold": gold.replace("DT_", "")}
        for name, fn in PATHS.items():
            top = fn(c["query"])
            hit1 = top[:1] == [gold]
            hit3 = gold in top[:3]
            mrr = 1.0 / (top.index(gold) + 1) if gold in top else 0.0
            agg[name]["h1"] += hit1
            agg[name]["h3"] += hit3
            agg[name]["mrr"] += mrr
            row[name] = "①" if hit1 else ("③" if hit3 else "✗")
        per_case.append(row)
    return agg, per_case


def main():
    n = len(cases)
    agg, per_case = evaluate()

    print(f"\n=== EXP-001: 매핑 경로 비교  (평가 {n}건, 통계표 {len(tables)}개) ===\n")
    print(f"{'경로':<22}{'Hit@1':>8}{'Hit@3':>8}{'MRR':>8}")
    print("-" * 46)
    for name, m in agg.items():
        print(f"{name:<22}{m['h1']/n:>8.2f}{m['h3']/n:>8.2f}{m['mrr']/n:>8.3f}")

    print(f"\n--- 케이스별 (① Hit@1 / ③ Hit@3 / ✗ 실패) ---")
    hdr = f"{'질의':<28}{'정답':<10}"
    for name in PATHS:
        hdr += f"{name.split('.')[0].split('(')[0][:6]:>8}"
    print(hdr)
    for r in per_case:
        line = f"{r['query']:<28}{r['gold']:<10}"
        for name in PATHS:
            line += f"{r[name]:>8}"
        print(line)

    # 결론 자동 도출
    best = max(agg.items(), key=lambda kv: (kv[1]["h3"], kv[1]["mrr"]))
    print(f"\n최고 경로: {best[0]} (Hit@3 {best[1]['h3']}/{n})")
    trap = [c for c in cases if "함정" in c.get("note", "")]
    print(f"함정 케이스 {len(trap)}건이 핵심 — 진짜 임베딩(HCX)이 오면 경로 B 자리에 교체해 재실험(스위치)")

    out = ROOT / "reports" / "exp001.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"n": n, "aggregate": agg, "per_case": per_case},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n리포트 저장: reports/exp001.json")


if __name__ == "__main__":
    main()
