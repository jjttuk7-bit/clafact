"""A2. 규칙 카드 레지스트리 — 카드를 '문서'가 아니라 '실행되는 자산'으로.

문서 11 원칙: "실패 1건 = 자산 1줄", "테스트 없는 규칙은 등록 불가".

지금까지 규칙 카드는 코드에 하드코딩된 동작을 *설명하는* JSON이었다.
이 모듈은 카드에 실행 가능한 `pattern`을 담을 수 있게 하여,
**카드를 추가하면 실제로 동작이 바뀌도록** 만든다 (문서 20 §3.1 플라이휠 폐쇄).

- `type: "detection"` + `pattern` → detect.is_candidate 가 런타임에 읽어 적용
- 그 외 타입(derived_calc 등)은 여전히 코드 구현이 필요한 '선언' 카드다.
  이 구분을 흐리지 않는다 — 자동 생성된 카드가 곧 자동 적용은 아니다.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

# 실제 카드 코퍼스에서 쓰는 타입 전부 (A2-0001~0012 스캔 기준).
# detection 만 '카드=실행'(pattern 필수)이고, 나머지는 코드 구현을 동반하는 선언 카드다.
RULE_TYPES = (
    "detection",     # 탐지 패턴 (런타임 실행)
    "derived_calc",  # 파생 계산 재현 (연령비율·증감률 등)
    "unit",          # 단위 환산·반올림
    "period",        # 시점 정규화·잠정치 회피
    "population",    # 모집단·분류 차원
    "extraction",    # 추출 가드
    "verdict",       # 판정 로직 (신뢰도 등)
    "normalization", "confidence", "guard", "bugfix", "correctness",
)

# 카드가 곧 실행인 타입 (pattern 필수)
EXECUTABLE_TYPES = ("detection",)

REQUIRED = ("rule_id", "type", "name", "condition", "handling")


class RuleRegistry:
    def __init__(self, rules_dir: str | Path = "data/assets/rules"):
        self.dir = Path(rules_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    # ── 조회 ──────────────────────────────────────────────
    def all(self) -> list[dict]:
        out = []
        for p in sorted(self.dir.glob("A2-*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError as e:
                raise ValueError(f"규칙 카드 파싱 실패: {p.name} — {e}") from e
        return out

    def __len__(self) -> int:
        return len(list(self.dir.glob("A2-*.json")))

    def next_id(self) -> str:
        """마지막 번호 + 1.

        문서 19 v1.0 초안이 기존 카드 수를 확인하지 않고 번호를 매겨
        A2-0009/0010 과 충돌했다. 채번은 사람이 세지 말고 이 함수로 한다.
        """
        nums = [0]
        for p in self.dir.glob("A2-*.json"):
            m = re.match(r"A2-(\d{4})", p.name)
            if m:
                nums.append(int(m.group(1)))
        for r in self.all():
            m = re.match(r"A2-(\d{4})", r.get("rule_id", ""))
            if m:
                nums.append(int(m.group(1)))
        return f"A2-{max(nums) + 1:04d}"

    def detection_patterns(self) -> list[tuple[str, str]]:
        """(rule_id, pattern) — detect 가 런타임에 적용할 탐지 패턴."""
        out = []
        for r in self.all():
            if r.get("type") == "detection" and r.get("pattern"):
                out.append((r["rule_id"], r["pattern"]))
        return out

    # ── 생성 ──────────────────────────────────────────────
    def create(
        self,
        type: str,
        name: str,
        condition: str,
        handling: str,
        origin_case: str = "",
        origin_run: str = "",
        test: str = "",
        pattern: str | None = None,
        rule_id: str | None = None,
    ) -> dict:
        """규칙 카드 1장 생성. 저장된 카드(dict) 반환."""
        if type not in RULE_TYPES:
            raise ValueError(f"type 은 {RULE_TYPES} 중 하나여야 합니다: {type}")
        name, condition, handling = (name or ""), (condition or ""), (handling or "")
        if not name.strip() or not condition.strip() or not handling.strip():
            raise ValueError("name·condition·handling 은 비울 수 없습니다.")
        if type in EXECUTABLE_TYPES:
            if not pattern or not pattern.strip():
                raise ValueError(
                    f"type={type} 은 실행 가능한 카드이므로 pattern(정규식)이 필수입니다."
                )
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"pattern 이 올바른 정규식이 아닙니다: {e}") from e

        rid = rule_id or self.next_id()
        # 선택 필드는 None 이 들어올 수 있다 (예: 리뷰 보정 없이 직접 입력한 실패 —
        # fail_id 가 None). 호출부마다 방어하게 두면 언젠가 빠뜨리므로 여기서 흡수한다.
        card = {
            "rule_id": rid,
            "type": type,
            "name": name.strip(),
            "condition": condition.strip(),
            "handling": handling.strip(),
            "origin_case": (origin_case or "").strip(),
            "origin_run": (origin_run or "").strip(),
            "test": (test or "").strip(),
            "created": time.strftime("%Y-%m-%d"),
        }
        if pattern:
            card["pattern"] = pattern
        slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", name.strip())[:40].strip("_")
        path = self.dir / f"{rid}_{slug or 'rule'}.json"
        if path.exists():
            raise FileExistsError(f"이미 존재하는 카드: {path.name}")
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return card

    def get(self, rule_id: str) -> dict | None:
        for r in self.all():
            if r.get("rule_id") == rule_id:
                return r
        return None

    def stats(self) -> dict:
        rows = self.all()
        by_type: dict[str, int] = {}
        for r in rows:
            by_type[r.get("type", "?")] = by_type.get(r.get("type", "?"), 0) + 1
        return {
            "total": len(rows),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "executable": sum(1 for r in rows if r.get("pattern")),
        }
