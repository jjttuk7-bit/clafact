"""2인 독립 라벨 대조 → 일치도 측정 · 불일치 중재 목록 · 골든셋 병합.

교차 라벨링의 값어치는 '두 번 했다'가 아니라 **두 사람이 갈린 지점**에 있다.
갈린 문장이 곧 라벨링 가이드가 모호한 지점이고, 그게 가이드 v2의 원료다.

절차
  1) 일치도 측정 — 단순 일치율 + Cohen's kappa(우연 일치 보정)
  2) 불일치 목록 → disagreements.csv (중재자가 최종 라벨을 적는다)
  3) 합의분만 골든셋에 병합 (중재 전 합류 금지 — 오염 방지)

사용:
    PYTHONPATH=. python scripts/merge_labels.py                 # 대조·리포트
    PYTHONPATH=. python scripts/merge_labels.py --merge         # 합의분 골든셋 병합
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT.parent / "news_data" / "labeling"
GOLDEN = ROOT / "data/goldenset/golden_v0.jsonl"

# 일치 여부를 따지는 핵심 필드 (수치·메모는 참고용이라 제외)
KEY_FIELDS = ["is_claim", "claim_type", "gold_label"]


def read(who: str) -> dict[str, dict]:
    p = DIR / f"goldenset_labels_{who}.csv"
    if not p.exists():
        sys.exit(f"라벨 파일 없음: {p}\n  → scripts/make_label_sheets.py 로 시트를 먼저 만드세요.")
    with p.open(encoding="utf-8-sig", newline="") as f:
        return {r["row_id"]: r for r in csv.DictReader(f)}


def norm(v: str) -> str:
    return (v or "").strip().lower()


def kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa — 우연히 맞을 확률을 뺀 일치도.

    단순 일치율은 라벨이 한쪽으로 쏠리면 부풀려진다(예: 90%가 match면
    아무렇게나 찍어도 81% 일치). kappa 는 그 착시를 걷어낸다.
    해석: 0.8↑ 우수 · 0.6~0.8 양호 · 0.6↓ 가이드 보완 필요
    """
    n = len(pairs)
    if n == 0:
        return 0.0
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="store_true", help="합의분을 골든셋에 병합")
    args = ap.parse_args()

    A, B = read("A"), read("B")
    ids = [i for i in A if i in B]
    if not ids:
        sys.exit("공통 row_id 가 없습니다 — 같은 시트로 라벨했는지 확인하세요.")

    labeled = [i for i in ids
               if any(norm(A[i].get(f)) for f in KEY_FIELDS)
               and any(norm(B[i].get(f)) for f in KEY_FIELDS)]
    if not labeled:
        sys.exit("아직 라벨이 비어 있습니다. 두 사람이 채운 뒤 다시 실행하세요.")

    print(f"=== 대조 대상 {len(labeled)}건 (전체 {len(ids)}건 중 양쪽 기입분)\n")

    agree_all: list[str] = []
    disagree: list[dict] = []
    for f in KEY_FIELDS:
        pairs = [(norm(A[i].get(f)), norm(B[i].get(f))) for i in labeled]
        hit = sum(1 for a, b in pairs if a == b)
        print(f"  {f:12} 일치 {hit}/{len(pairs)} ({hit/len(pairs):.1%})  ·  kappa {kappa(pairs):.3f}")

    for i in labeled:
        diffs = {f: (norm(A[i].get(f)), norm(B[i].get(f)))
                 for f in KEY_FIELDS if norm(A[i].get(f)) != norm(B[i].get(f))}
        if diffs:
            disagree.append({
                "row_id": i, "sentence": A[i]["sentence"],
                **{f"{f}_A": v[0] for f, v in diffs.items()},
                **{f"{f}_B": v[1] for f, v in diffs.items()},
                "notes_A": A[i].get("notes", ""), "notes_B": B[i].get("notes", ""),
                "final_is_claim": "", "final_claim_type": "", "final_gold_label": "",
                "중재_사유": "",
            })
        else:
            agree_all.append(i)

    print(f"\n  전 항목 합의 {len(agree_all)}건  ·  불일치 {len(disagree)}건 "
          f"({len(disagree)/len(labeled):.1%})")

    if disagree:
        p = DIR / "disagreements.csv"
        cols = sorted({k for d in disagree for k in d},
                      key=lambda k: (not k.startswith(("row_id", "sentence")), k))
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(disagree)
        print(f"  중재 목록: {p}")
        print("\n  ↳ 이 목록이 라벨링 가이드 v2 의 원료입니다. 왜 갈렸는지가 곧 모호한 규칙입니다.")

    if not args.merge:
        print("\n(합의분을 골든셋에 넣으려면 --merge)")
        return 0

    # ── 병합: 합의분만. 중재 전 불일치는 넣지 않는다 ──
    from clafact.assets import goldenset
    added = skipped = 0
    for i in agree_all:
        r = A[i]
        if norm(r.get("is_claim")) not in ("true", "1", "y", "yes", "t"):
            continue                      # 비주장은 음성 표본으로만 쓰고 골든셋 행은 만들지 않는다
        try:
            goldenset.append_row(
                GOLDEN, r["sentence"], True, norm(r.get("gold_label")) or None,
                claimed_value=float(r["claimed_value"]) if r.get("claimed_value") else None,
                claimed_unit=r.get("claimed_unit") or "",
            )
            added += 1
        except ValueError:
            skipped += 1                  # 중복·라벨 누락은 레지스트리가 거부
    print(f"\n골든셋 병합: 추가 {added}건 · 거부 {skipped}건 → {GOLDEN}")
    print("불일치 건은 중재 후 별도로 추가하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
