"""릴리스 게이트 (문서 12 §5.1) — 데모·파일럿 공개 전 필수 통과.

자동 검사 가능한 게이트는 스크립트가 판정하고, 사람 검토 게이트는 체크리스트로 출력한다.
"판정 규칙: 하나라도 고위험 항목이 실패하면 출시하지 않는다." (플레이북 템플릿 04)

사용법: python scripts/release_gate.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

# 임계값 (문서 05 초기 목표 — 골든셋 확정 후 캘리브레이션)
THRESHOLDS = {"detection_f1": 0.80, "verdict_accuracy": 0.75, "fallback_f1": 0.80}

# 시크릿 패턴 (고위험 게이트)
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"),
    re.compile(r"nv-[A-Za-z0-9]{20,}"),  # NCP 계열 키 형태
]
SCAN_EXCLUDE = {".git", "__pycache__", "reports", ".env.example"}


def run_cmd(args: list[str]) -> tuple[int, str]:
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def gate_tests() -> tuple[bool, str]:
    """게이트: 전 단위 테스트 통과 — '테스트 없는 규칙은 등록 불가'의 집행."""
    for mod in ("tests.test_verdict", "tests.test_detect", "tests.test_parse",
                "tests.test_ingest", "tests.test_retrieve", "tests.test_run"):
        code, out = run_cmd([sys.executable, "-m", mod])
        if code != 0:
            return False, f"{mod} 실패"
    return True, "전 테스트 통과"


def gate_harness() -> tuple[bool, str]:
    """게이트: 하네스 실행 + 지표 임계값 (평균만 보지 않도록 클래스별 F1 도 출력)."""
    from clafact.eval.harness import run
    report = run(str(ROOT / "data/goldenset/golden_v0.jsonl"),
                 str(ROOT / "reports"), record_failures=False)
    m = report["metrics"]
    vals = {
        "detection_f1": m["detection"]["f1"],
        "verdict_accuracy": m["verdict"]["classification"]["accuracy"],
        "fallback_f1": m["verdict"]["fallback"]["f1"],
    }
    fails = [f"{k}={v} < {THRESHOLDS[k]}" for k, v in vals.items() if v < THRESHOLDS[k]]
    detail = ", ".join(f"{k}={v}" for k, v in vals.items())
    return (not fails), (detail if not fails else "; ".join(fails))


def gate_secrets() -> tuple[bool, str]:
    """게이트(고위험): 저장소 내 자격정보 노출 스캔."""
    hits = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(part in SCAN_EXCLUDE for part in p.parts):
            continue
        if p.suffix in (".pyc", ".png", ".jpg", ".pdf", ".docx"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                hits.append(str(p.relative_to(ROOT)))
                break
    return (not hits), ("노출 없음" if not hits else f"의심 파일: {', '.join(hits)}")


def gate_contamination() -> tuple[bool, str]:
    """게이트: 골든셋 오염 방지 — 파이프라인 코드가 골든셋을 참조하면 안 된다 (WF-3)."""
    bad = []
    for p in (ROOT / "clafact" / "pipeline").rglob("*.py"):
        if "goldenset" in p.read_text(encoding="utf-8", errors="ignore"):
            bad.append(str(p.relative_to(ROOT)))
    return (not bad), ("오염 없음" if not bad else f"골든셋 참조 발견: {', '.join(bad)}")


def gate_version() -> tuple[bool, str]:
    """게이트: 버전 태깅 가능 상태 — git 커밋 존재 + 작업 트리 상태 보고."""
    code, out = run_cmd(["git", "rev-parse", "--short", "HEAD"])
    if code != 0:
        return False, "git 저장소 아님 — 롤백 불가"
    rev = out.strip()
    _, status = run_cmd(["git", "status", "--porcelain"])
    dirty = bool(status.strip())
    return True, f"HEAD={rev}" + (" (미커밋 변경 있음 — 릴리스 전 커밋 필요)" if dirty else " (클린)")


MANUAL_GATES = [
    "[제품] 리포트에 근거 통계·계산 과정·한계가 표시되는가 (리뷰 화면 확인)",
    "[제품] 판단불가 사유가 사용자에게 노출되는가",
    "[안전] 미확정(IN_REVIEW) 판정이 외부로 나가지 않는가",
    "[회복] 오판정 대응 절차(WF-7C) 리허설을 1회 수행했는가",
    "[승인] 골든셋 오너가 세그먼트별 결과를 검토·승인했는가",
]


def main() -> int:
    gates = [
        ("테스트", gate_tests, True),
        ("지표 임계", gate_harness, True),
        ("시크릿 스캔", gate_secrets, True),   # 고위험
        ("골든셋 오염", gate_contamination, True),
        ("버전·롤백", gate_version, False),
    ]
    print("\n=== ClaFact 릴리스 게이트 (문서 12 §5.1) ===\n")
    all_pass = True
    for name, fn, critical in gates:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"게이트 실행 오류: {e}"
        mark = "PASS" if ok else ("FAIL(고위험)" if critical else "WARN")
        if not ok and critical:
            all_pass = False
        print(f"  [{mark:11s}] {name:8s} — {detail}")
    print("\n--- 사람 검토 게이트 (자동화 불가 — 출시 승인 전 체크) ---")
    for item in MANUAL_GATES:
        print(f"  [ ] {item}")
    print(f"\n자동 게이트 종합: {'통과 — 사람 검토 게이트 확인 후 공개 가능' if all_pass else '실패 — 출시 불가'}\n")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
