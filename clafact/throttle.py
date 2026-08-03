"""호출 예산·레이트 리미터 — KOSIS 호출을 안전하게 관리하기 위한 장치.

[2026-08-03 정정] 이전 버전은 "개발 계정 트래픽 1,000회"를 문서 19 §5.2·§5.3에서
인용한 KOSIS 공식 한도로 서술했다. KOSIS 공식 서비스 소개(공유서비스 안내)를 원문
대조한 결과, 공식 문서에 명시된 것은 **"호출 빈도 제한: 분당 200번 이내"**와
**"데이터 호출 제한: 40,000셀(요청 1회당)"**뿐이며, "누적 총 1,000회" 같은 계정
총량 한도는 확인되지 않았다. 문서 19의 "1,000회" 항목은 같은 문서의 다른 항목(분당
제한의 공지일자, 40,000건 등)과 달리 출처 표기가 없어 근거가 불명확하다 — 진짜
KOSIS 한도인지, 아니면 사실이 아닌 채로 문서에 들어간 것인지 재확인이 필요하다.

`CallBudget`의 상한(`limit`)은 이제 "KOSIS가 정한 한도"가 아니라 **우리가 비용·오남용
방지를 위해 자체적으로 설정한 안전 상한**으로 이해해야 한다. 확인된 실제 제약은
`RateLimiter`가 다루는 **분당 200회**뿐이다.

설계 원칙: 한도를 넘기면 **조용히 실패하지 말고 시끄럽게 멈춘다.**
한도 초과는 429/차단으로 돌아오고, 그때는 이미 예산이 없다.
남은 호출 수를 세면서 미리 막는 쪽이 낫다.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class BudgetExceeded(RuntimeError):
    """예산 소진 — 더 호출하면 계정 한도를 태운다."""


class RateLimiter:
    """분당 호출 수 제한 (슬라이딩 윈도우).

    [2026-08-03] KOSIS 공식 서비스 소개에 "호출 빈도 제한: 분당 200번 이내"로
    명시돼 있음을 원문으로 확인했다. 기본값은 이 확인된 수치에 10% 안전 여유를 둔
    180으로 둔다. 이전 기본값(30)은 미확인 상태에서의 보수적 추정치였다.
    """

    def __init__(self, per_minute: int = 180):
        if per_minute < 1:
            raise ValueError("per_minute 은 1 이상이어야 합니다")
        self.per_minute = per_minute
        self._hits: list[float] = []
        self._lock = threading.Lock()

    def acquire(self, sleep=time.sleep) -> float:
        """호출 직전에 부른다. 필요하면 대기하고, 대기한 초를 반환."""
        with self._lock:
            now = time.monotonic()
            self._hits = [t for t in self._hits if now - t < 60.0]
            waited = 0.0
            if len(self._hits) >= self.per_minute:
                waited = 60.0 - (now - self._hits[0]) + 0.01
                if waited > 0:
                    sleep(waited)
                    now = time.monotonic()
                    self._hits = [t for t in self._hits if now - t < 60.0]
            self._hits.append(now)
            return max(waited, 0.0)


class CallBudget:
    """누적 호출 수를 파일에 기록하며 상한을 강제한다.

    프로세스가 죽어도 카운터가 살아야 한다 — 하네스를 열 번 돌리면
    열 번의 호출이 모두 같은 상한 안에서 나가기 때문이다.

    [2026-08-03] `limit` 기본값(1,000)은 KOSIS가 공식적으로 강제하는 계정 총량
    한도가 아니라, 확인 전까지 보수적으로 유지하는 **자체 안전 상한**이다.
    KOSIS 공식 문서에서 확인된 것은 `RateLimiter`가 다루는 분당 200회뿐이다.
    """

    def __init__(self, path: str | Path = "data/cache/call_budget.json",
                 limit: int = 1000, warn_at: float = 0.8):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit = limit
        self.warn_at = warn_at
        self._lock = threading.Lock()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"used": 0, "since": time.strftime("%Y-%m-%d"), "log": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"used": 0, "since": time.strftime("%Y-%m-%d"), "log": []}

    def used(self) -> int:
        return int(self._load().get("used", 0))

    def remaining(self) -> int:
        return max(self.limit - self.used(), 0)

    def check(self, n: int = 1) -> None:
        """호출 전 확인. 초과면 BudgetExceeded — 호출하기 *전에* 멈춘다."""
        if self.used() + n > self.limit:
            raise BudgetExceeded(
                f"자체 안전 상한 소진: {self.used()}/{self.limit} 사용됨 "
                f"(이 상한은 KOSIS 공식 한도가 아니라 우리가 정한 값입니다). "
                f"캐시 활용을 먼저 확인하고, 필요하면 CallBudget(limit=...) 을 조정하세요."
            )

    def spend(self, n: int = 1, note: str = "") -> int:
        """호출 후 기록. 남은 수 반환."""
        with self._lock:
            d = self._load()
            d["used"] = int(d.get("used", 0)) + n
            log = d.get("log", [])
            log.append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": n, "note": note[:80]})
            d["log"] = log[-200:]  # 최근 것만 — 로그 파일이 무한히 자라지 않게
            self.path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            return max(self.limit - d["used"], 0)

    def should_warn(self) -> bool:
        return self.used() >= self.limit * self.warn_at

    def reset(self) -> None:
        """계정 한도가 갱신됐을 때만 쓴다."""
        self.path.write_text(
            json.dumps({"used": 0, "since": time.strftime("%Y-%m-%d"), "log": []},
                       ensure_ascii=False, indent=2), encoding="utf-8")

    def stats(self) -> dict:
        d = self._load()
        return {"used": int(d.get("used", 0)), "limit": self.limit,
                "remaining": self.remaining(), "since": d.get("since", "")}


def backoff_delays(tries: int = 4, base: float = 1.0, cap: float = 20.0) -> list[float]:
    """지수 백오프 지연 목록 — 분당 제한에 걸렸을 때 재시도 간격."""
    return [min(base * (2 ** i), cap) for i in range(tries)]
