"""평가 지표 계산 (문서 05 지표 체계의 구현)."""
from __future__ import annotations


def prf1(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn}


def classification_report(gold: list[str], pred: list[str]) -> dict:
    """다중 분류 정확도 + 클래스별 P/R/F1."""
    assert len(gold) == len(pred)
    labels = sorted(set(gold) | set(pred))
    acc = sum(1 for g, q in zip(gold, pred) if g == q) / len(gold) if gold else 0.0
    per_class = {}
    for lb in labels:
        tp = sum(1 for g, q in zip(gold, pred) if g == lb and q == lb)
        fp = sum(1 for g, q in zip(gold, pred) if g != lb and q == lb)
        fn = sum(1 for g, q in zip(gold, pred) if g == lb and q != lb)
        per_class[lb] = prf1(tp, fp, fn)
    macro_f1 = sum(v["f1"] for v in per_class.values()) / len(per_class) if per_class else 0.0
    return {"accuracy": round(acc, 4), "macro_f1": round(macro_f1, 4),
            "per_class": per_class, "n": len(gold)}


def fallback_metrics(gold: list[str], pred: list[str], fallback_label: str = "unverifiable") -> dict:
    """판단불가(Fallback)의 P/R — 오판정은 미판정보다 나쁘다는 원칙의 측정 (문서 05)."""
    tp = sum(1 for g, q in zip(gold, pred) if g == fallback_label and q == fallback_label)
    fp = sum(1 for g, q in zip(gold, pred) if g != fallback_label and q == fallback_label)
    fn = sum(1 for g, q in zip(gold, pred) if g == fallback_label and q != fallback_label)
    return prf1(tp, fp, fn)
