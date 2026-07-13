"""A5 평가 하네스 실행 — 한 줄로 전 지표.

사용법:
    python scripts/run_eval.py
    python scripts/run_eval.py --golden data/goldenset/golden_v0.jsonl --no-failures
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 콘솔(cp949) 대응 — 하네스 출력은 항상 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clafact.eval.harness import run, print_summary


def main():
    ap = argparse.ArgumentParser(description="ClaFact 평가 하네스 (A5)")
    ap.add_argument("--golden", default="data/goldenset/golden_v0.jsonl")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--no-failures", action="store_true", help="A4 실패 레코드 기록 생략")
    args = ap.parse_args()

    report = run(args.golden, args.out, record_failures=not args.no_failures)
    print_summary(report)


if __name__ == "__main__":
    main()
