"""LLM 클라이언트 추상화 — HCX 연동과 mock 모드의 공통 인터페이스.

키 도착 전: MockLLMClient 로 파이프라인 E2E 개발.
키 도착 후: HcxClient 로 교체 (인터페이스 동일).
용도별 모델 분업(문서 04 §4): 판별·분류=DASH, 추출·설명=HCX-003+.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path
from typing import Callable, Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str, *, model: str = "", temperature: float = 0.0) -> str:
        ...


def signature(system: str, user: str, model: str) -> str:
    """요청의 결정적 서명 — 카세트 키. 키·시크릿은 포함하지 않는다."""
    raw = json.dumps([system, user, model], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


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
    """NCP CLOVA Studio HCX API (Chat Completions v3). HCX_API_KEY 환경변수 필요.

    엔드포인트: /v3/chat-completions/{model} (구 /testapp/v1 아님 — 2026-07 실측 400 후 정정).
    헤더: Authorization Bearer + X-NCP-CLOVASTUDIO-REQUEST-ID(UUID) + Content-Type.
    temperature 0 고정 권장 — 멱등성(WF-1 운영 규칙).
    """

    BASE = "https://clovastudio.stream.ntruss.com/v3/chat-completions"

    def __init__(self, api_key: str | None = None, timeout: int = 60):
        self.api_key = api_key or os.environ.get("HCX_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError("HCX_API_KEY 가 없습니다 — .env 설정 또는 MockLLMClient 사용")

    def complete(self, system: str, user: str, *, model: str = "HCX-005", temperature: float = 0.0) -> str:
        import uuid
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
                     "X-NCP-CLOVASTUDIO-REQUEST-ID": uuid.uuid4().hex,
                     "Content-Type": "application/json",
                     "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        # v3 비스트리밍 응답: {"result": {"message": {"content": "..."}}}
        return data.get("result", {}).get("message", {}).get("content", "")


class Cassette:
    """record-replay 카세트 — 요청 서명 → 응답. **API 키는 저장하지 않는다.**

    저장 형식: {signature: {system, user, model, response}}.
    system/user는 사람이 리뷰할 수 있게 평문 보관(프롬프트 회귀의 근거).
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.entries: dict[str, dict] = {}
        if self.path.exists():
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, system: str, user: str, model: str) -> str | None:
        e = self.entries.get(signature(system, user, model))
        return e["response"] if e else None

    def put(self, system: str, user: str, model: str, response: str) -> None:
        self.entries[signature(system, user, model)] = {
            "system": system, "user": user, "model": model, "response": response,
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=2), encoding="utf-8")


class ReplayLLMClient:
    """카세트에 녹화된 응답만 재생 — 오프라인·결정적·무과금.

    카세트에 없는 요청은 RuntimeError(테스트가 조용히 통과하지 않게).
    실 API 검증은 record_hcx.py 로 카세트를 갱신하는 방식으로 한다.
    """

    def __init__(self, cassette: Cassette):
        self.cassette = cassette
        self.calls: list[dict] = []

    def complete(self, system: str, user: str, *, model: str = "HCX-005", temperature: float = 0.0) -> str:
        self.calls.append({"system": system, "user": user, "model": model})
        resp = self.cassette.get(system, user, model)
        if resp is None:
            raise RuntimeError(
                f"카세트에 없는 요청 (sig={signature(system, user, model)}). "
                "scripts/record_hcx.py 로 녹화 필요.")
        return resp


class RecordingHcxClient:
    """실 HCX 호출 + 카세트 자동 저장 — record_hcx.py 에서만 쓴다.

    이 클래스만 실 API를 호출한다. 키는 HcxClient가 환경변수에서 읽고,
    카세트에는 응답만 남는다(키 미저장).
    """

    def __init__(self, cassette: Cassette, inner: LLMClient | None = None):
        self.cassette = cassette
        self.inner = inner or HcxClient()

    def complete(self, system: str, user: str, *, model: str = "HCX-005", temperature: float = 0.0) -> str:
        resp = self.inner.complete(system, user, model=model, temperature=temperature)
        self.cassette.put(system, user, model, resp)
        return resp


def get_client() -> LLMClient:
    """키가 있으면 HCX, 없으면 mock — 파이프라인 코드는 이 함수만 호출한다."""
    if os.environ.get("HCX_API_KEY"):
        return HcxClient()
    return MockLLMClient()
