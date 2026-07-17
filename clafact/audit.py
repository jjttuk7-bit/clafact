"""감사 추적 — "이 판정을 어떻게 재현하는가"를 판정마다 남긴다.

기업이 사업화를 검토할 때 실제로 묻는 것은 정확도가 아니라 **감사 가능성**이다
(문서 20 §3 기능 3). "AI가 그렇게 판단했습니다"는 업무에 못 쓴다.
"이 통계표의 이 파라미터로 이 값을 받아, 이 규칙으로 이렇게 계산했습니다.
 이 URL을 직접 열어 확인하십시오"라야 쓴다.

담는 것:
  - code_version : 판정 당시 코드(git) — 재현의 전제
  - engine       : Fixture(오프라인) / Http(실 API) — 어느 쪽인지 숨기지 않는다
  - table        : orgId·tblId·통계표명 + 매핑 점수(왜 이 표가 뽑혔는가)
  - params       : 조회 파라미터 전체
  - url          : 실 호출과 **같은 코드**로 만든 URL (인증키는 자리표시자)
  - rows         : 판정에 실제로 쓰인 행
  - rules        : 적용된 규칙 카드 ID
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from clafact.kosis import build_url

_rev_cache: dict[str, str] = {}


def code_version(root: Path | None = None) -> str:
    """git short rev. 실패 시 'nogit' — 재현 불가를 숨기지 않는다."""
    r = root or Path(__file__).resolve().parents[1]
    key = str(r)
    if key in _rev_cache:
        return _rev_cache[key]
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, cwd=r, timeout=5)
        rev = out.stdout.strip() or "nogit"
    except Exception:
        rev = "nogit"
    _rev_cache[key] = rev
    return rev


@dataclass
class AuditTrail:
    code_version: str = ""
    engine: str = ""
    org_id: str = ""
    tbl_id: str = ""
    tbl_name: str = ""
    match_score: float | None = None
    params: dict = field(default_factory=dict)
    url: str = ""
    rows: list[dict] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "code_version": self.code_version, "engine": self.engine,
            "org_id": self.org_id, "tbl_id": self.tbl_id, "tbl_name": self.tbl_name,
            "match_score": self.match_score, "params": self.params, "url": self.url,
            "rows": self.rows, "rules": self.rules, "note": self.note,
        }


def build(engine_name: str, org_id: str, tbl_id: str, tbl_name: str,
          params: dict, rows: list[dict], rules: list[str],
          match_score: float | None = None) -> AuditTrail:
    """감사 추적 1건 생성. url 은 인증키 자리표시자가 들어간 안전한 형태."""
    fixture = "Fixture" in engine_name
    return AuditTrail(
        code_version=code_version(),
        engine=engine_name,
        org_id=org_id, tbl_id=tbl_id, tbl_name=tbl_name,
        match_score=match_score,
        params=params,
        url=build_url(org_id, tbl_id, **params),
        rows=rows,
        rules=rules,
        note=("픽스처(오프라인) 모드로 판정했습니다. 위 URL 은 실 API 호출 시 사용되는 "
              "형식으로, 2026-07-14 실 API 스모크 테스트로 검증된 형태입니다."
              if fixture else "실 KOSIS API 응답으로 판정했습니다."),
    )
