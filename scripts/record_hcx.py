"""HCX 카세트 녹화 — **키가 있는 환경에서 R2가 실행**한다 (실 API 호출).

이 스크립트만 실 HCX를 부른다. 카세트에는 응답만 남고 키는 저장되지 않는다.
녹화된 tests/cassettes/hcx/smoke.json 은 커밋 가능(키 없음) → CI에서 오프라인 재생.

사용:
    # .env 의 키를 환경변수로 (셸 기록에 남지 않게 주의)
    export HCX_API_KEY=$(grep ^HCX_API_KEY .env | cut -d= -f2)
    PYTHONPATH=. python scripts/record_hcx.py

재녹화(실 API 응답 구조가 바뀌었을 때)도 같은 명령. 기존 항목은 덮어쓴다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clafact.llm import Cassette, RecordingHcxClient  # noqa: E402

# 녹화할 프롬프트 세트 — 계약 테스트가 재생할 케이스.
# (system, user, model) — 실제 파이프라인이 쓸 프롬프트에 맞춰 확장한다.
CASES = [
    (
        "당신은 뉴스 문장이 검증 가능한 수치 주장인지 판별하는 분류기다. "
        'JSON으로만 답하라: {"verifiable": true|false, "reason": "..."}',
        "다음 문장을 판별하라: 지난해 실업률은 7.2%로 전년보다 0.3%p 상승했다.",
        "HCX-005",
    ),
    (
        "당신은 뉴스 문장이 검증 가능한 수치 주장인지 판별하는 분류기다. "
        'JSON으로만 답하라: {"verifiable": true|false, "reason": "..."}',
        "다음 문장을 판별하라: 내년 성장률은 3%로 전망된다.",
        "HCX-005",
    ),
    (
        "당신은 뉴스 문장에서 수치 주장의 구성요소를 추출하는 도구다. "
        'JSON으로만 답하라: {"indicator","period","unit","value"}',
        "다음에서 추출하라: 지난해 출생아 수는 23만 명으로 역대 최저였다.",
        "HCX-005",
    ),
]


def main() -> int:
    if not os.environ.get("HCX_API_KEY"):
        print("HCX_API_KEY 환경변수가 없습니다. .env 에서 export 후 실행하세요.", file=sys.stderr)
        return 1
    out = Path(__file__).resolve().parents[1] / "tests/cassettes/hcx/smoke.json"
    cass = Cassette(out)
    client = RecordingHcxClient(cass)
    ok = 0
    for system, user, model in CASES:
        try:
            resp = client.complete(system, user, model=model)
            print(f"[녹화] {user[:40]}... → {resp[:60]!r}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"[실패] {user[:40]}... → {type(e).__name__}: {e}", file=sys.stderr)
    cass.save()
    print(f"\n카세트 저장: {out} ({ok}/{len(CASES)}건). 키는 저장되지 않음 — 커밋 가능.")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
