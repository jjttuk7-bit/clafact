"""Step 1: 질의 생성 — 주장 문장에서 통계표 '검색어'를 뽑는다.

경로 C(KOSIS 통합검색)는 자연어 문장이 아니라 검색어를 받는다. 문장째 넣으면
숫자·날짜·서술어가 RANK 를 흐린다. 실측(2026-07-15): '과수 농가 고령'조차 원하는
표가 1위가 아니었다 — 검색어 품질이 매핑 성패를 가른다 (구현/검색매핑_구현가이드 Step 1).

규칙 버전(지금): 별칭 치환(기사어→통계어) + 숫자·날짜·단위·시점어 제거.
LLM 버전(HCX 후): 핵심 지표어 추출을 보강 — 인터페이스는 동일하게 둔다.
"""
from __future__ import annotations

import re

from clafact.assets.alias_dict import AliasDict

# 날짜 (검색어에서 노이즈)
RE_DATE = re.compile(r"\d{0,4}\s*년|\d{1,2}\s*월|\d{1,2}\s*일|[1-4]\s*분기")

# 수량 스팬 = 숫자(+스케일)(+단위) 를 통째로 제거한다.
#   ⚠️ 단위어(가구·명·인 등)를 '단독 토큰'으로 지우면 안 된다 — '150만 가구'(수량)는 노이즈지만
#      '1인 가구'(주제)의 '가구'는 핵심어다. 숫자에 붙은 단위만 스팬으로 제거해 주제어를 살린다.
_UNITS = "%p|%|퍼센트|포인트|명|가구|건|원|배|위|톤|호|인|세대|세"
RE_QTY_SPAN = re.compile(rf"\d[\d,.]*\s*[천만억조]?\s*(?:{_UNITS})?")

# 2글자 이상 한글/영문 토큰 (조사가 붙은 어절 단위)
RE_TOKEN = re.compile(r"[가-힣A-Za-z]{2,}")

# 검색에 도움 안 되는 시점 상대어 (지표어가 아님)
STOP_TIME = frozenset({
    "올해", "금년", "지난해", "작년", "전년", "내년", "재작년",
    "최근", "이번", "지난달", "당해", "매년", "예년",
})

# 검색에 도움 안 되는 서술·평가 어절 (문장 노이즈). 어절 끝 조사까지 포함해 보수적으로.
STOP_PREFIX = (
    "나타", "늘었", "늘어", "줄었", "줄어", "증가", "감소", "급증", "급감",
    "상승", "하락", "기록", "달했", "달해", "넘어", "밑돌", "웃돌", "불과",
    "이르", "전망", "예상", "분석", "심각", "지적", "우려", "밝혔", "보인",
    "대한", "관련", "위한", "따르", "대해",
)

# 흔한 조사 접미 (어절 끝에서 벗겨 통계어 토큰만 남김)
JOSA = ("으로써", "으로", "에서", "에게", "까지", "부터", "보다", "이라는", "라는",
        "이라", "에는", "에도", "의", "은", "는", "이", "가", "을", "를",
        "에", "도", "와", "과", "및", "들")


def _strip_josa(tok: str) -> str:
    for j in sorted(JOSA, key=len, reverse=True):
        if tok.endswith(j) and len(tok) - len(j) >= 2:
            return tok[: -len(j)]
    return tok


def _is_noise(tok: str) -> bool:
    if tok in STOP_TIME:
        return True
    if any(tok.startswith(p) for p in STOP_PREFIX):
        return True
    return False


def make_query(sentence: str, aliases: AliasDict | None = None,
               extra_terms: list[str] | None = None) -> str:
    """주장 문장 → 통계표 검색어 (통계어 위주, 노이즈 제거).

    순서: ① 별칭 치환(가장 큰 레버) ② 숫자·날짜 제거 ③ 토큰화·조사 제거·노이즈 컷.
    반환: 공백으로 이은 검색어. 비면 원문 폴백(빈 검색어보다 낫다).
    """
    aliases = aliases if aliases is not None else AliasDict()
    text = aliases.substitute(sentence)          # ① 기사어 → 통계어
    text = RE_DATE.sub(" ", text)                # ② 날짜 → 수량스팬 순서로 제거
    text = RE_QTY_SPAN.sub(" ", text)            #    '150만 가구'는 지우되 '가구'는 살림

    terms: list[str] = []
    seen: set[str] = set()
    for raw in RE_TOKEN.findall(text):           # ③ 토큰화
        tok = _strip_josa(raw)
        if len(tok) < 2 or _is_noise(tok) or tok in seen:
            continue
        seen.add(tok)
        terms.append(tok)

    for t in (extra_terms or []):                # 지표·모집단 힌트(LLM 슬롯) 추가 여지
        if t and t not in seen:
            seen.add(t)
            terms.append(t)

    return " ".join(terms) if terms else sentence.strip()


def make_query_variants(sentence: str, aliases: AliasDict | None = None) -> list[str]:
    """검색 후보 여러 개 — 각각 검색 후 RRF 융합용 (경로 C/D).

    [정제 검색어, 별칭 치환 원문] — 정제가 과해 핵심어를 놓쳤을 때의 안전망.
    """
    aliases = aliases if aliases is not None else AliasDict()
    q1 = make_query(sentence, aliases)
    q2 = aliases.substitute(sentence)
    out, seen = [], set()
    for q in (q1, q2):
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out
