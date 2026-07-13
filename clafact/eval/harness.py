"""A5. 평가 하네스 — 명령 한 줄로 전 지표 실행·비교·실패 덤프.

원칙(문서 11): "하네스에 없는 지표는 없는 지표".
- 골든셋 버전·코드 버전(git)·타임스탬프를 리포트에 기록 (재현성, NFR-04)
- 이전 실행과 자동 비교 (개선/악화 표시)
- 오답은 FailureRecorder 로 자동 기록 (A4 배선)
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from clafact.pipeline import detect
from clafact.pipeline.verdict import compare
from clafact.eval.metrics import prf1, classification_report, fallback_metrics
from clafact.assets.failures import FailureRecorder


def git_rev(cwd: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        ).stdout.strip() or "nogit"
    except Exception:
        return "nogit"


def load_golden(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def eval_detection(rows: list[dict]) -> dict:
    """1단계: 규칙 필터의 주장 탐지 성능 (골든셋 is_claim 대비)."""
    tp = fp = fn = tn = 0
    misses = []
    for r in rows:
        pred = detect.is_candidate(r["sentence"])
        gold = bool(r["is_claim"])
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
            misses.append(("detect_fp", r))
        elif not pred and gold:
            fn += 1
            misses.append(("detect_fn", r))
        else:
            tn += 1
    out = prf1(tp, fp, fn)
    out["tn"] = tn
    return {"metrics": out, "misses": misses}


def eval_verdict(rows: list[dict]) -> dict:
    """2단계: 판정 엔진 성능 — evidence 가 주어진 주장에 대해 3분류 판정."""
    gold_labels, pred_labels = [], []
    misses = []
    for r in rows:
        if not r.get("is_claim") or r.get("gold_label") is None:
            continue
        gold = r["gold_label"]
        if r.get("evidence_value") is None:
            pred = "unverifiable"  # 대응 통계 부재 → Fallback (문서 10 WF-1 5단계)
        else:
            res = compare(
                claimed=float(r["claimed_value"]),
                claimed_unit=r.get("claimed_unit", ""),
                official=float(r["evidence_value"]),
                official_unit=r.get("evidence_unit", ""),
                op=r.get("claimed_op", "eq"),
            )
            pred = res.verdict.label.value
        gold_labels.append(gold)
        pred_labels.append(pred)
        if pred != gold:
            misses.append(("verdict_wrong", {**r, "predicted": pred}))
    report = classification_report(gold_labels, pred_labels) if gold_labels else {}
    fb = fallback_metrics(gold_labels, pred_labels) if gold_labels else {}
    return {"metrics": {"classification": report, "fallback": fb}, "misses": misses}


def diff_with_previous(report: dict, latest_path: Path) -> dict:
    """이전 latest 와 핵심 지표 비교."""
    if not latest_path.exists():
        return {}
    prev = json.loads(latest_path.read_text(encoding="utf-8"))
    keys = {
        "detection_f1": ("detection", "f1"),
        "verdict_accuracy": ("verdict", "classification", "accuracy"),
        "fallback_f1": ("verdict", "fallback", "f1"),
    }
    diff = {}
    for name, path in keys.items():
        def dig(d, p):
            for k in p:
                d = d.get(k, {}) if isinstance(d, dict) else {}
            return d if isinstance(d, (int, float)) else None
        now, before = dig(report["metrics"], path), dig(prev.get("metrics", {}), path)
        if now is not None and before is not None:
            diff[name] = {"prev": before, "now": now, "delta": round(now - before, 4)}
    return diff


def run(golden_path: str, out_dir: str = "reports", record_failures: bool = True) -> dict:
    root = Path(__file__).resolve().parents[2]
    golden = Path(golden_path)
    rows = load_golden(golden)

    run_id = time.strftime("%Y%m%d_%H%M%S")
    det = eval_detection(rows)
    ver = eval_verdict(rows)

    report = {
        "run_id": run_id,
        "golden": {"path": str(golden), "n_rows": len(rows)},
        "code_version": git_rev(root),
        "metrics": {"detection": det["metrics"], "verdict": ver["metrics"]},
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    latest = out / "latest.json"
    report["diff_vs_previous"] = diff_with_previous(report, latest)

    # A4 배선: 오답 자동 기록
    n_failures = 0
    if record_failures:
        rec = FailureRecorder(root / "data/failures/failures.jsonl")
        for kind, row in det["misses"] + ver["misses"]:
            ftype = "detection" if kind.startswith("detect") else "verdict"
            rec.record(
                stage="eval",
                ftype=ftype,
                snapshot={"kind": kind, "sentence": row.get("sentence", ""),
                          "gold": row.get("gold_label") or row.get("is_claim"),
                          "predicted": row.get("predicted")},
                run_id=run_id,
            )
            n_failures += 1
    report["failures_recorded"] = n_failures

    (out / f"eval_{run_id}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def print_summary(report: dict) -> None:
    m = report["metrics"]
    print(f"\n=== ClaFact 평가 리포트  run={report['run_id']}  code={report['code_version']} ===")
    print(f"골든셋: {report['golden']['path']} ({report['golden']['n_rows']}행)")
    d = m["detection"]
    print(f"\n[주장 탐지 — 규칙 필터] P={d['precision']} R={d['recall']} F1={d['f1']} "
          f"(tp={d['tp']} fp={d['fp']} fn={d['fn']} tn={d['tn']})")
    v = m["verdict"].get("classification", {})
    if v:
        print(f"[판정 3분류] Acc={v['accuracy']} MacroF1={v['macro_f1']} (n={v['n']})")
        for lb, s in v["per_class"].items():
            print(f"  - {lb:13s} P={s['precision']} R={s['recall']} F1={s['f1']}")
        fb = m["verdict"]["fallback"]
        print(f"[Fallback(판단불가)] P={fb['precision']} R={fb['recall']} F1={fb['f1']}")
    if report.get("diff_vs_previous"):
        print("\n[전 회차 대비]")
        for k, d2 in report["diff_vs_previous"].items():
            arrow = "▲" if d2["delta"] > 0 else ("▼" if d2["delta"] < 0 else "=")
            print(f"  {k}: {d2['prev']} → {d2['now']} ({arrow}{abs(d2['delta'])})")
    print(f"\n실패 레코드 자동 기록: {report['failures_recorded']}건 → data/failures/failures.jsonl")
    print("원칙: 실패 1건 = 자산 1줄 — resolve 시 파생 자산 ID 필수\n")
