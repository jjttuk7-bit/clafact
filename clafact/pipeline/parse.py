"""규칙 기반 Claim Parser (FR-05의 비-LLM 부분).

HCX 없이 정규식으로 갈 수 있는 데까지 간다:
  - 수치·단위 추출: "1,234가구", "7.2%", "0.3%p", "23만 명", "150만 가구"
  - 상대 시점 정규화 (규칙 A2-0005): "올해"/"지난해"/"작년 3분기" → 작성일 기준 절대 시점
  - 임계·추세 표현 감지 (규칙 A2-0001 연동): "넘어섰다"→gte, "밑돌았다"→lte

지표명(metric)·모집단(population) 추출은 규칙으로 어려워 LLM 단계(HCX 연동 후)로 남긴다.
이 모듈이 확실히 추출한 필드는 LLM 출력과 교차 검증하는 가드로도 쓴다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

# ── 수치·단위 ────────────────────────────────────────────────
SCALES = {"천": 1_000.0, "만": 10_000.0, "억": 100_000_000.0, "조": 1_000_000_000_000.0}
UNITS = "%p|%|퍼센트|포인트|명|가구|건|원|배|위|톤|ha|㎢|호|인|세대"

RE_QTY = re.compile(
    rf"(?P<num>\d{{1,3}}(?:,\d{{3}})+|\d+(?:\.\d+)?)\s*"
    rf"(?P<scale>[천만억조])?\s*"
    rf"(?P<unit>{UNITS})?"
)
# 날짜 성분(년/월/일/분기/개월/차)은 수치가 아니다
RE_DATE_TAIL = re.compile(r"^\s*(년|월|일|분기|개월|차|시|분(?![기])|초)")

# 규칙 A2-0006: 복합명사 가드 — "1인 가구", "3인 가족"의 숫자는 수량이 아니라 명사의 일부
RE_COMPOUND_TAIL = re.compile(r"^\s*(가구|가족|가정|체제|기업|승|실(?![적]))")


@dataclass
class Quantity:
    value: float                 # 표기된 값 (예: "23만 명" → 23)
    scale: str = ""              # 천/만/억/조
    unit: str = ""               # %, 명, 가구 …
    composed_unit: str = ""      # verdict 엔진 단위 (scale+unit, 예: "만명")
    normalized_value: float = 0.0  # scale 반영 절대값 (예: 230000)
    span: tuple[int, int] = (0, 0)
    raw: str = ""


def extract_quantities(sentence: str) -> list[Quantity]:
    """문장에서 수치 후보를 추출한다. 날짜 성분은 제외."""
    out: list[Quantity] = []
    for m in RE_QTY.finditer(sentence):
        num, scale, unit = m.group("num"), m.group("scale") or "", m.group("unit") or ""
        tail = sentence[m.end():]
        # 단위·스케일이 없고 뒤가 날짜 성분이면 스킵 ("2024년", "3월", "1분기")
        if not unit and RE_DATE_TAIL.match(tail):
            continue
        # 복합명사 가드 (규칙 A2-0006): "1인 가구"의 '1인'은 수량이 아니다
        if unit in ("인", "명") and RE_COMPOUND_TAIL.match(tail):
            continue
        # 단위도 스케일도 없는 맨숫자는 소수점 있는 경우만 채택 (지표성 높음)
        if not unit and not scale and "." not in num:
            continue
        value = float(num.replace(",", ""))
        factor = SCALES.get(scale, 1.0)
        out.append(Quantity(
            value=value, scale=scale, unit=unit,
            composed_unit=(scale + unit) if scale and unit else (unit or scale),
            normalized_value=value * factor,
            span=m.span(), raw=m.group(0).strip(),
        ))
    return out


# ── 시점 정규화 (규칙 A2-0005) ────────────────────────────────
REL_YEAR = {"올해": 0, "금년": 0, "이번 해": 0, "지난해": -1, "작년": -1,
            "전년": -1, "재작년": -2, "내년": 1, "이듬해": 1}

RE_ABS_YM = re.compile(r"(\d{4})년\s*(\d{1,2})월")
RE_MONTH_RANGE = re.compile(r"\d{1,2}\s*[~∼-]\s*(\d{1,2})월")
RE_ABS_YQ = re.compile(r"(\d{4})년\s*([1-4])분기")
RE_ABS_Y = re.compile(r"(\d{4})년")
RE_REL_Q = re.compile(r"(올해|금년|지난해|작년|전년|재작년|내년)\s*([1-4])분기")
RE_REL_M = re.compile(r"(올해|금년|지난해|작년|전년|재작년|내년)\s*(\d{1,2})월")
RE_REL_Y = re.compile(r"올해|금년|지난해|작년|전년(?!\s*동기)|재작년|내년")
RE_LAST_MONTH = re.compile(r"지난달|지난 달|전월")
RE_Q_ONLY = re.compile(r"([1-4])분기")

# 비교 '기준'을 가리키는 어구 — 주장의 시점이 아니다.
# "지난달 물가가 **작년 같은 달보다** 2.2% 올랐다"에서 시점은 지난달이지 작년이 아니다.
# 이 어구를 지우지 않으면 RE_REL_Y('작년')가 시점을 가로채 엉뚱한 연도로 조회한다
# (실측 2026-07-20: 월간 주장이 전부 전년도로 조회돼 '자료 없음'으로 빠졌다).
RE_BASELINE = re.compile(
    r"전년\s*동월\s*대비|전년\s*동기\s*대비|전년\s*대비|작년\s*같은\s*달(보다)?|"
    r"지난해\s*같은\s*(달|기간|분기)(보다)?|작년\s*동월(보다)?|작년보다|지난해보다")


def _to_date(article_date) -> date:
    if isinstance(article_date, date):
        return article_date
    if isinstance(article_date, datetime):
        return article_date.date()
    s = str(article_date).strip()[:10].replace(".", "-").replace("/", "-")
    return datetime.strptime(s, "%Y-%m-%d").date()


def normalize_period(sentence: str, article_date) -> str:
    """상대 시점 표현을 기사 작성일 기준 절대 시점 문자열로 변환.

    반환 형식: "YYYY" | "YYYY-MM" | "YYYY-Qn" | "" (미검출)
    우선순위: 절대 연월 > 절대 연분기 > 상대 연+분기/월 > 절대 연 > 상대 연 > 지난달 > 분기 단독
    """
    base = _to_date(article_date)
    # 비교 기준 어구를 먼저 제거 — 주장의 시점과 비교 대상 시점을 혼동하지 않기 위해
    sentence = RE_BASELINE.sub(" ", sentence)

    if m := RE_ABS_YM.search(sentence):
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    if m := RE_MONTH_RANGE.search(sentence):
        return f"{base.year}-{int(m.group(1)):02d}"
    if m := RE_ABS_YQ.search(sentence):
        return f"{m.group(1)}-Q{m.group(2)}"
    if m := RE_REL_Q.search(sentence):
        return f"{base.year + REL_YEAR[m.group(1)]}-Q{m.group(2)}"
    if m := RE_REL_M.search(sentence):
        return f"{base.year + REL_YEAR[m.group(1)]}-{int(m.group(2)):02d}"
    if m := RE_ABS_Y.search(sentence):
        return m.group(1)
    if m := RE_REL_Y.search(sentence):
        return str(base.year + REL_YEAR[m.group(0)])
    if RE_LAST_MONTH.search(sentence):
        y, mth = (base.year, base.month - 1) if base.month > 1 else (base.year - 1, 12)
        return f"{y}-{mth:02d}"
    if m := RE_Q_ONLY.search(sentence):
        return f"{base.year}-Q{m.group(1)}"  # 연도 미지정 분기는 작성 연도로 가정
    return ""


# ── 임계·추세 표현 (규칙 A2-0001 연동) ───────────────────────
RE_GTE = re.compile(r"넘어서|넘어섰|넘었|넘겼|돌파|웃돌|상회")  # 활용형 주의: 섰≠서
RE_LTE = re.compile(r"밑돌|하회|그쳤|그쳐|불과")
RE_UP = re.compile(r"증가|늘어|늘었|급증|상승|올랐")
RE_DOWN = re.compile(r"감소|줄어|줄었|급감|하락|떨어졌|떨어져")


def detect_op(sentence: str) -> str:
    """비교 연산자 감지: gte(임계 초과) / lte(임계 미만) / eq(기본)."""
    if RE_GTE.search(sentence):
        return "gte"
    if RE_LTE.search(sentence):
        return "lte"
    return "eq"


def detect_trend(sentence: str) -> str:
    """증감 방향: up / down / '' — 증감형 주장의 부호 검증에 사용."""
    if RE_UP.search(sentence):
        return "up"
    if RE_DOWN.search(sentence):
        return "down"
    return ""


# ── 통합 ──────────────────────────────────────────────────────
@dataclass
class ParsedClaim:
    sentence: str
    quantities: list[Quantity] = field(default_factory=list)
    period: str = ""
    op: str = "eq"
    trend: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def parse_complete(self) -> bool:
        """규칙만으로 검증 진행 가능한 최소 조건 (수치+시점)."""
        return bool(self.quantities) and bool(self.period)


def parse_claim(sentence: str, article_date) -> ParsedClaim:
    """규칙 기반 1차 파싱. LLM 단계는 이 결과를 채우거나 교차 검증한다."""
    pc = ParsedClaim(
        sentence=sentence,
        quantities=extract_quantities(sentence),
        period=normalize_period(sentence, article_date),
        op=detect_op(sentence),
        trend=detect_trend(sentence),
    )
    if not pc.quantities:
        pc.notes.append("수치 미검출 — LLM 추출 필요 또는 판단불가 후보")
    if not pc.period:
        pc.notes.append("시점 미검출 — 기사 작성 연도로 가정하거나 LLM 확인 필요")
    return pc
