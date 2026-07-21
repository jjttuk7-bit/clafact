"""골든셋 후보 200건 층화 추출 → 2인 독립 라벨링 시트 생성.

**이 스크립트는 라벨을 만들지 않는다.** 후보 문장을 고르고 빈 라벨 칸을 준 뒤,
두 사람이 서로를 보지 않고 각자 채운다. LLM·분류기 출력이 골든셋에 들어가면
평가 체계 전체가 오염된다(가드레일).

층화 기준
  - 도메인: KOSIS 후보의 실제 분포를 따른다(인구가구·고용·물가·농가)
  - 주장 유형: 규모/증감/파생계산/임계가 고루 들어가게 상한을 둔다
  - 음성 표본: 검증 대상이 아닌 문장(범위 밖·전망·비주장)을 15% 섞는다
    → is_claim=False 를 라벨러가 판단할 기회가 없으면 탐지 정밀도를 잴 수 없다

사용:
    PYTHONPATH=. python scripts/make_label_sheets.py            # 200건
    PYTHONPATH=. python scripts/make_label_sheets.py --n 100 --seed 7
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clafact.pipeline import source_classify as sc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIED = ROOT.parent / "news_data" / "claims_classified_v01.json"
OUT_DIR = ROOT.parent / "news_data" / "labeling"

# 라벨러가 채울 칸 (빈 값으로 발행)
LABEL_COLS = ["is_claim", "claim_type", "gold_label", "claimed_value",
              "claimed_unit", "evidence_value", "evidence_unit", "notes"]
FIXED_COLS = ["row_id", "sentence", "article_date", "source_hint", "domain_hint"]

# 도메인별 목표 비율 — KOSIS 후보 실제 분포(인구가구 337·고용 271·물가 130·농가 82)를 반영
DOMAIN_WEIGHT = {
    "population_household": 0.38,
    "employment_labor": 0.31,
    "prices_inflation": 0.19,
    "agriculture_fishery": 0.12,
}
NEGATIVE_SHARE = 0.15   # 음성 표본(검증 대상 아님) 비중


def load() -> list[dict]:
    """분류 결과를 읽되 **현재 규칙으로 다시 분류한다**.

    저장된 JSON은 A2-0014(해외 가드)·키워드 정정 이전에 만들어졌다. 그대로 층화하면
    '어가' 부분일치 오탐(들어가·이어가기로)이 농가 표본을 차지해 실제 농가 문장이
    4건밖에 안 뽑힌다(실측). 규칙이 좋아질수록 표본도 좋아지게 재분류가 맞다.
    """
    if not CLASSIFIED.exists():
        sys.exit(f"분류 데이터 없음: {CLASSIFIED}\n"
                 "  → scripts/map_dataset_kosis.py --dry-run 을 먼저 돌리거나 데이터를 배치하세요.")
    recs = json.loads(CLASSIFIED.read_text(encoding="utf-8"))
    out = []
    for r in recs:
        lbl = sc.classify(r["sentence"])
        out.append({**r, "source_type": lbl.source_type,
                    "domain": lbl.domain, "claim_type": lbl.claim_type})
    return out


def pick(recs: list[dict], n: int, rng: random.Random) -> list[dict]:
    """도메인·주장유형 층화 + 음성 표본 혼합."""
    kosis = [r for r in recs if r.get("source_type", "").startswith("KOSIS")]
    others = [r for r in recs if not r.get("source_type", "").startswith("KOSIS")]

    n_neg = round(n * NEGATIVE_SHARE)
    n_pos = n - n_neg

    # ── 양성: 도메인 비율 × 주장유형 분산 ──
    by_dom: dict[str, list[dict]] = defaultdict(list)
    for r in kosis:
        by_dom[r.get("domain", "-")].append(r)

    picked: list[dict] = []
    for dom, w in DOMAIN_WEIGHT.items():
        quota = round(n_pos * w)
        pool = by_dom.get(dom, [])
        if not pool:
            continue
        # 주장 유형이 한쪽으로 쏠리지 않게 유형별로 나눠 담는다
        by_type: dict[str, list[dict]] = defaultdict(list)
        for r in pool:
            by_type[r.get("claim_type", "규모형")].append(r)
        types = sorted(by_type, key=lambda t: -len(by_type[t]))
        per = max(1, quota // max(len(types), 1))
        got: list[dict] = []
        for t in types:
            rng.shuffle(by_type[t])
            got += by_type[t][:per]
        # 모자라면 남은 풀에서 채운다
        if len(got) < quota:
            rest = [r for r in pool if r not in got]
            rng.shuffle(rest)
            got += rest[:quota - len(got)]
        picked += got[:quota]

    # ── 음성: 비-KOSIS(범위 밖·전망·플랫폼 등) 고루 ──
    by_src: dict[str, list[dict]] = defaultdict(list)
    for r in others:
        by_src[r.get("source_type", "UNKNOWN")].append(r)
    neg: list[dict] = []
    srcs = list(by_src)
    rng.shuffle(srcs)
    i = 0
    while len(neg) < n_neg and srcs:
        s = srcs[i % len(srcs)]
        if by_src[s]:
            neg.append(by_src[s].pop(rng.randrange(len(by_src[s]))))
        else:
            srcs.remove(s)
            continue
        i += 1
    picked += neg

    rng.shuffle(picked)          # 라벨러가 순서로 유형을 눈치채지 못하게
    return picked[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = pick(load(), args.n, rng)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sheet: list[dict] = []
    for i, r in enumerate(rows, 1):
        s = r["sentence"]
        lbl = sc.classify(s)          # 힌트일 뿐 — 라벨이 아니다
        sheet.append({
            "row_id": f"G{i:03d}",
            "sentence": s,
            "article_date": r.get("date", ""),
            # 힌트는 '참고'이지 정답이 아니다. 라벨러는 힌트와 다르게 판단해도 된다.
            "source_hint": lbl.source_type,
            "domain_hint": lbl.domain,
            **{c: "" for c in LABEL_COLS},
        })

    for who in ("A", "B"):
        p = OUT_DIR / f"goldenset_labels_{who}.csv"
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIXED_COLS + LABEL_COLS)
            w.writeheader()
            w.writerows(sheet)
        print(f"라벨링 시트: {p}")

    key = OUT_DIR / "candidates.jsonl"
    with key.open("w", encoding="utf-8") as f:
        for row in sheet:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n후보 {len(sheet)}건 (seed={args.seed})")
    print("  source_hint:", dict(Counter(r["source_hint"] for r in sheet).most_common()))
    print("  domain_hint:", dict(Counter(r["domain_hint"] for r in sheet).most_common()))
    print("\n두 사람이 각자 파일을 열어 **서로 보지 않고** 채운 뒤,")
    print("  PYTHONPATH=. python scripts/merge_labels.py   ← 일치도·불일치 목록 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
