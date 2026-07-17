"""호출 예산·레이트 리미터 — KOSIS 1,000회 한도에서 살아남기 위한 장치.

문서 19 §5.2·§5.3 의 결론:
  - 개발 계정 트래픽은 **1,000회**. 골든셋 200~300 주장 × 후보 표 3~5개 × 메타 조회를
    곱하면 **평가 배치 1회로 소진**된다. 하네스는 반복 실행이 전제이므로
    캐시·예산 가드는 성능 최적화가 아니라 **생존 조건**이다.
  - **분당 호출 제한**이 존재한다 (2026.02.05 / 2026.07.09 공지).

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

    KOSIS 가 공지한 분당 제한의 정확한 수치는 미확인이므로(문서 19 §8.4),
    보수적 기본값을 쓰고 공지 확인 후 조정한다. 모르면 느리게 가는 편이 안전하다.
    """

    def __init__(self, per_minute: int = 30):
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
    열 번의 호출이 모두 같은 계정 한도에서 나가기 때문이다.
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
                f"KOSIS 호출 예산 소진: {self.used()}/{self.limit} 사용됨. "
                f"운영 계정 증량 신청 또는 캐시 활용이 필요합니다 (문서 19 §5.2). "
                f"한도를 늘리려면 CallBudget(limit=...) 을 조정하세요."
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
