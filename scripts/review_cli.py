"""검증자 리뷰 CLI (WF-2 프로토타입) — 승인/보정/반려 흐름과 A4 배선 검증.

사용법:
    python scripts/review_cli.py --demo   # 큐만 출력 (비대화형)
    python scripts/review_cli.py          # 대화형 리뷰

리뷰 큐 정렬 (규칙 A2-0004): 불일치 → confidence low → medium → high.
보정(correct)은 실패 레코드로 기록되어 다음 골든셋·규칙의 원료가 된다.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clafact.pipeline.verdict import compare
from clafact.assets.failures import FailureRecorder

CONF_ORDER = {"low": 0, "medium": 1, "high": 2, None: 3}
LABEL_ORDER = {"mismatch": 0, "unverifiable": 1, "match": 2}


def build_queue(golden_path: Path) -> list[dict]:
    """골든셋에서 자동 판정을 생성해 리뷰 큐를 만든다 (데모용 — 실전은 WF-1 산출물)."""
    queue = []
    with golden_path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if not r.get("is_claim") or r.get("claimed_value") is None:
                continue
            if r.get("evidence_value") is None:
                item = {"label": "unverifiable", "confidence": None,
                        "reason": "대응 통계 부재", "calculation": "-"}
            else:
                res = compare(float(r["claimed_value"]), r.get("claimed_unit", ""),
                              float(r["evidence_value"]), r.get("evidence_unit", ""),
                              op=r.get("claimed_op", "eq"))
                v = res.verdict
                item = {"label": v.label.value, "confidence": v.confidence,
                        "reason": v.reason, "calculation": v.calculation}
            item.update({"id": f"{r['article_id']}-{r['sentence_id']}", "sentence": r["sentence"]})
            queue.append(item)
    return sorted(queue, key=lambda x: (LABEL_ORDER[x["label"]], CONF_ORDER[x["confidence"]]))


def show(item: dict, idx: int, total: int) -> None:
    conf = item["confidence"] or "-"
    print(f"\n[{idx}/{total}] {item['id']}  판정={item['label']}  신뢰도={conf}")
    print(f"  문장: {item['sentence']}")
    print(f"  근거: {item['reason']}  |  계산: {item['calculation']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="ClaFact 리뷰 CLI (WF-2)")
    ap.add_argument("--golden", default="data/goldenset/golden_v0.jsonl")
    ap.add_argument("--demo", action="store_true", help="큐만 출력하고 종료")
    args = ap.parse_args()

    queue = build_queue(Path(args.golden))
    print(f"=== 리뷰 큐 {len(queue)}건 (정렬: 불일치 → low → medium → high) ===")

    if args.demo:
        for i, item in enumerate(queue, 1):
            show(item, i, len(queue))
        print("\n(--demo 모드 — 대화형 리뷰는 옵션 없이 실행)")
        return 0

    rec = FailureRecorder("data/failures/failures.jsonl")
    stats = {"approve": 0, "correct": 0, "reject": 0, "skip": 0}
    for i, item in enumerate(queue, 1):
        show(item, i, len(queue))
        try:
            act = input("  [a]승인 [c]보정 [r]반려 [s]건너뛰기 > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if act == "a":
            stats["approve"] += 1          # → CONFIRMED
        elif act == "c":
            correct = input("  올바른 판정 (match/mismatch/unverifiable) > ").strip()
            why = input("  보정 사유 (탐지/추출/매핑/정렬/판정/설명 중 원인) > ").strip()
            fid = rec.record(stage="review", ftype="verdict",
                             snapshot={"id": item["id"], "sentence": item["sentence"],
                                       "auto": item["label"], "corrected": correct},
                             cause=why)
            print(f"  → CORRECTED 기록 {fid} — 파생 자산 등록 후 resolve 필수!")
            stats["correct"] += 1
        elif act == "r":
            stats["reject"] += 1           # → REJECTED (재처리)
        else:
            stats["skip"] += 1
    print(f"\n리뷰 결과: {stats}")
    print(f"보정률(사람이 뒤집은 비율): {stats['correct']}/{sum(stats.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
