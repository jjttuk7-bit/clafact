"""클라우드 도달 스모크 — 실 HCX·KOSIS가 이 환경에서 응답하는지 1회씩 확인.

목적: '스위치가 진짜로 당겨지는가'의 최초 증명. 개발망(정부망 443 차단)에서는
불가능하므로 클라우드(GitHub Actions·NCP 등)에서 돌린다.

안전: 키는 환경변수에서만 읽고 **출력하지 않는다**. 성공/실패·응답 길이·검색
건수만 보고한다. KOSIS는 예산 1회 소모(도달 증명 값어치).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def check_hcx() -> bool:
    if not os.environ.get("HCX_API_KEY"):
        print("[HCX] 건너뜀 — HCX_API_KEY 미설정")
        return False
    from clafact.llm import HcxClient
    try:
        resp = HcxClient(timeout=30).complete(
            "예/아니오로만 답하라.",
            "다음 문장에 수치가 있는가: 실업률은 7.2%였다.")
        ok = bool(resp and resp.strip())
        print(f"[HCX] {'✅ 도달' if ok else '⚠️ 빈 응답'} — 응답 {len(resp)}자")
        return ok
    except Exception as e:  # noqa: BLE001
        print(f"[HCX] ❌ 실패 — {type(e).__name__}: {str(e)[:120]}")
        return False


def check_kosis() -> bool:
    if not os.environ.get("KOSIS_API_KEY"):
        print("[KOSIS] 건너뜀 — KOSIS_API_KEY 미설정")
        return False
    from clafact.kosis import HttpKosisClient
    from clafact.pipeline.retrieve_kosis import search_kosis
    try:
        hits = search_kosis("실업률", HttpKosisClient(timeout=30), top_k=5)
        print(f"[KOSIS] ✅ 도달 — 통합검색 '실업률' 후보 {len(hits)}건")
        for h in hits[:3]:
            print(f"        · {h.tbl_id} {h.tbl_name[:40]}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[KOSIS] ❌ 실패 — {type(e).__name__}: {str(e)[:160]}")
        return False


def main() -> int:
    print("=== 클라우드 도달 스모크 ===")
    hcx = check_hcx()
    kosis = check_kosis()
    print("\n=== 결론 ===")
    print(f"HCX  : {'도달됨 — LLM 2차 판별 실연동 가능' if hcx else '미도달'}")
    print(f"KOSIS: {'도달됨 — 경로 C 실검색·매핑 가능' if kosis else '미도달'}")
    if hcx and kosis:
        print("→ 이 클라우드에서 실 서비스 파이프라인을 돌릴 수 있습니다.")
        return 0
    if not (hcx or kosis):
        print("→ 둘 다 미도달. 이 환경(해외 IP?)이 막혔을 수 있음 — 국내 클라우드(NCP) 시도.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
