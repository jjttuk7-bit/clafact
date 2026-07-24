"""1차 규칙 필터 — 수치·비교 표현 포함 문장 선별 (FR-02).

설계(문서 03 2.2): 규칙 필터는 재현율(놓치지 않기)을 책임지고,
정밀도는 2차 LLM 판별이 보강한다. LLM 판별은 HCX 연동 후 detect_llm.py 로 추가.

탐지 패턴의 두 갈래 (문서 20 §3.1):
  1) 아래 하드코딩 패턴 — 초기 구축분. 각각 규칙 카드가 문서로 존재한다.
  2) 규칙 카드의 `pattern` — 런타임에 읽어 적용한다. **카드를 추가하면 동작이 바뀐다.**
     플라이휠(실패 → 규칙 → 재평가 개선)이 실제로 도는 것은 이 두 번째 갈래 덕분이다.
"""
from __future__ import annotations

import re
from pathlib import Path

# 숫자(콤마·소수점 포함) — "1,234", "7.2", "64.2" 등
NUM = r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?"

# 수치 뒤에 붙을 때 주장성이 높은 단위·표현
UNIT_HINT = r"(?:%|%p|퍼센트|포인트|명|가구|건|원|배|위|개|톤|ha|㎢|호|인|세대?)"

# 증감·비교·규모 표현 (유형 분류의 힌트이기도 함) — 활용형 주의: 섰≠서 (A2 경험칙)
TREND_HINT = (
    r"(?:증가|감소|늘어|늘었|줄어|줄었|급증|급감|상승|하락|최고|최저|최대|최소|"
    r"확대|축소|경신|돌파|넘어서|넘어섰|넘었|밑돌|웃돌|기록|차지|달해|달했|불과)"
)

# 숫자 + (스케일: 천/만/억/조)? + 단위 — "1억 원", "150만 가구" 대응
RE_NUM_UNIT = re.compile(rf"(?:{NUM})\s*[천만억조]?\s*{UNIT_HINT}")
RE_NUM = re.compile(NUM)
RE_TREND = re.compile(TREND_HINT)

# 규칙 A2-0003: 숫자 없는 최상급 주장 — "사상 최악", "역대 최저" 등은
# 수치 없이도 통계로 검증 가능한 주장이다 (유래: F20260713142141-0828)
RE_SUPERLATIVE = re.compile(r"(?:사상|역대)\s*(?:최악|최고|최대|최소|최저|최다)")

# 검증 대상이 아닐 가능성이 높은 패턴 (날짜·전화번호 등 노이즈 컷)
RE_NOISE_ONLY = re.compile(r"^\s*(?:\d{4}년\s*)?\d{1,2}월\s*\d{1,2}일\s*$")
RE_SITE_CHROME = re.compile(r"(?:실시간\s*뉴스|뉴스\s*\d+\s*분\s*전|구독하기|로그인|더보기)")

# ── 규칙 카드에서 오는 탐지 패턴 ──────────────────────────────
RULES_DIR = Path(__file__).resolve().parents[2] / "data" / "assets" / "rules"

# 캐시 무효화 = 플라이휠의 속도. 규칙을 만들자마자 재평가에 반영돼야 한다.
#
# ⚠ 디렉터리 mtime 으로 감지하면 안 된다 — Windows(NTFS)에서는 파일을 새로 만들어도
#   상위 디렉터리의 mtime 이 갱신되지 않는 경우가 있다(실측 확인, tests/test_rules.py).
#   그 경우 카드를 추가해도 낡은 캐시가 계속 쓰여 "규칙을 만들었는데 점수가 그대로"인
#   조용한 실패가 난다. 그래서 카드 파일 목록 자체를 지문으로 쓴다.
_cache: dict[str, object] = {"sig": None, "pats": []}


def _signature(d: Path) -> tuple:
    """규칙 카드 파일들의 (이름, 크기, mtime) 지문."""
    out = []
    for p in sorted(d.glob("A2-*.json")):
        try:
            st = p.stat()
            out.append((p.name, st.st_size, st.st_mtime_ns))
        except OSError:
            continue
    return (str(d), tuple(out))


def rule_patterns(rules_dir: str | Path | None = None) -> list[tuple[str, re.Pattern]]:
    """규칙 카드의 detection 패턴을 (rule_id, 컴파일된 정규식)으로 반환."""
    d = Path(rules_dir) if rules_dir else RULES_DIR
    if not d.exists():
        return []
    sig = _signature(d)
    if _cache["sig"] == sig:
        return _cache["pats"]  # type: ignore[return-value]

    from clafact.assets.rules import RuleRegistry  # 순환 import 방지 — 지연 로드

    pats = []
    for rid, pattern in RuleRegistry(d).detection_patterns():
        try:
            pats.append((rid, re.compile(pattern)))
        except re.error:
            # 깨진 패턴 하나가 파이프라인 전체를 멈추면 안 된다 — 건너뛰고 계속
            continue
    _cache["sig"], _cache["pats"] = sig, pats
    return pats


def reload_rules() -> int:
    """캐시 강제 무효화. 반환값은 로드된 패턴 수."""
    _cache["sig"] = None
    return len(rule_patterns())


def mixed_claim_reason(sentence: str) -> str | None:
    """여러 제목 조각·수치가 합쳐진 크롤링 산출물은 자동 매핑하지 않는다."""
    if len(re.findall(r"(?:\.{3}|…)", sentence)) >= 2 and len(RE_NUM_UNIT.findall(sentence)) >= 2:
        return "복합 기사 조각 — 서로 다른 수치·주제가 섞여 자동 KOSIS 검증 제외"
    return None


def exclusion_reason(sentence: str) -> str | None:
    """Return a user-facing reason when a sentence is crawler chrome, not article text."""
    if RE_SITE_CHROME.search(sentence):
        return "실시간 뉴스·사이트 크롬"
    return None


def is_candidate(sentence: str) -> bool:
    """검증 가능 주장 '후보' 여부 — 재현율 우선, 관대한 기준."""
    s = sentence.strip()
    if not s or RE_NOISE_ONLY.match(s) or exclusion_reason(s):
        return False
    # 숫자+단위 조합이 있으면 후보
    if RE_NUM_UNIT.search(s):
        return True
    # 숫자와 증감·비교 표현이 함께 있으면 후보
    if RE_NUM.search(s) and RE_TREND.search(s):
        return True
    # 숫자 없는 최상급 주장 (규칙 A2-0003)
    if RE_SUPERLATIVE.search(s):
        return True
    # 규칙 카드에서 온 탐지 패턴 — 실패에서 태어난 자산이 여기서 실행된다
    for _rid, rx in rule_patterns():
        if rx.search(s):
            return True
    return False


def which_rule(sentence: str) -> str | None:
    """이 문장을 탐지한 규칙 카드 ID (없으면 None) — 데모에서 '왜 잡혔는지' 표시용."""
    for rid, rx in rule_patterns():
        if rx.search(sentence.strip()):
            return rid
    return None


def filter_sentences(sentences: list[str]) -> list[tuple[int, str]]:
    """(인덱스, 문장) 리스트로 후보 반환."""
    return [(i, s) for i, s in enumerate(sentences) if is_candidate(s)]
