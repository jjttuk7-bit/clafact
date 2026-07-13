"""1차 규칙 필터 — 수치·비교 표현 포함 문장 선별 (FR-02).

설계(문서 03 2.2): 규칙 필터는 재현율(놓치지 않기)을 책임지고,
정밀도는 2차 LLM 판별이 보강한다. LLM 판별은 HCX 연동 후 detect_llm.py 로 추가.
"""
from __future__ import annotations

import re

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


def is_candidate(sentence: str) -> bool:
    """검증 가능 주장 '후보' 여부 — 재현율 우선, 관대한 기준."""
    s = sentence.strip()
    if not s or RE_NOISE_ONLY.match(s):
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
    return False


def filter_sentences(sentences: list[str]) -> list[tuple[int, str]]:
    """(인덱스, 문장) 리스트로 후보 반환."""
    return [(i, s) for i, s in enumerate(sentences) if is_candidate(s)]
