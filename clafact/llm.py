"""LLM 클라이언트 추상화 — HCX 연동과 mock 모드의 공통 인터페이스.

키 도착 전: MockLLMClient 로 파이프라인 E2E 개발.
키 도착 후: HcxClient 로 교체 (인터페이스 동일).
용도별 모델 분업(문서 04 §4): 판별·분류=DASH, 추출·설명=HCX-003+.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable, Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str, *, model: str = "", temperature: float = 0.0) -> str:
        ...


class MockLLMClient:
    """개발용 mock — 등록된 핸들러 또는 canned 응답을 돌려준다.

    사용: mock = MockLLMClient(); mock.on("주장 판별", lambda u: '{"verifiable": true}')
    """

    def __init__(self, default: str = "{}"):
        self.default = default
        self.handlers: list[tuple[str, Callable[[str], str]]] = []
        self.calls: list[dict] = []  # 호출 로그 — 프롬프트 회귀 테스트에 사용

    def on(self, system_contains: str, handler: Callable[[str], str]) -> None:
        self.handlers.append((system_contains, handler))

    def complete(self, system: str, user: str, *, model: str = "", temperature: float = 0.0) -> str:
        self.calls.append({"system": system, "user": user, "model": model})
        for key, fn in self.handlers:
            if key in system:
                return fn(user)
        return self.default


class HcxClient:
    """NCP CLOVA Studio HCX API. HCX_API_KEY 환경변수 필요.

    ⚠️ 키 발급 후 엔드포인트·요청 형식을 NCP 콘솔 문서 기준으로 검증할 것.
    temperature 0 고정 권장 — 멱등성(WF-1 운영 규칙).
    """

    BASE = "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions"

    def __init__(self, api_key: str | None = None, timeout: int = 60):
        self.api_key = api_key or os.environ.get("HCX_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError("HCX_API_KEY 가 없습니다 — .env 설정 또는 MockLLMClient 사용")

    def complete(self, system: str, user: str, *, model: str = "HCX-005", temperature: float = 0.0) -> str:
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature, "topP": 0.8, "maxTokens": 1024,
        }
        req = urllib.request.Request(
            f"{self.BASE}/{model}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("result", {}).get("message", {}).get("content", "")


def get_client() -> LLMClient:
    """키가 있으면 HCX, 없으면 mock — 파이프라인 코드는 이 함수만 호출한다."""
    if os.environ.get("HCX_API_KEY"):
        return HcxClient()
    return MockLLMClient()
