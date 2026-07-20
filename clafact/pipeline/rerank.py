"""통계표 후보 재순위 (경로 C 2단계) — 결정적 규칙 기반.

왜 필요한가: KOSIS 통합검색은 짧은 지표어로 후보 10개를 잘 물어오지만, RANK 1위가
주장에 맞는 표라는 보장이 없다. 실측(2026-07-20)에서 '소비자물가' 질의의 1위는
`e-지방지표 소비자물가 등락률(시도/시)`(지역·연간)이었고, 정작 월간 주장에 필요한
`월별 소비자물가 등락률`(DT_1J22042)은 7위에 있었다. 그 결과 월간 주장이 연간
지역값과 대조돼 오'불일치'가 났다.

왜 LLM이 아니라 규칙인가: 어느 표를 왜 골랐는지 설명할 수 있어야 감사(재현 URL)가
성립한다. 판정이 결정적 코드인 것과 같은 이유다. 규칙으로 안 풀리는 애매한 경우에만
상위 단계에서 LLM 리랭커를 얹는다.

신호는 통합검색 응답에 이미 들어 있다(추가 호출 0원):
  VW_CD      MT_ZTITLE(국내 주제별) / MT_RTITLE(국제기구) / MT_GTITLE01(지역지표)
  TBL_NM     '월별'·'연도별'·'(시도' 등 주기·범위 표기
  STAT_NM    소비자물가조사 / e-지방지표 / IMF / OECD / 가계동향조사 …
  MT_ATITLE  분류 경로('국제기구별 통계 > IMF …')
  STRT/END_PRD_DE  수록기간
"""
from __future__ import annotations

import re

# 월 단위 주장 표지 (run.py A2-0015 와 같은 개념 — 순환 import 방지를 위해 별도 정의)
RE_MONTHLY = re.compile(r"지난달|전월|이달|당월|전년\s*동월|작년\s*같은\s*달|\d{1,2}월\b|월간|월별")
RE_ANNUAL = re.compile(r"연간|지난해\s*연간|한 해|연도별|작년 한 해")
# 지역 주장 표지 — 있으면 지역표가 오히려 정답
RE_REGION = re.compile(
    r"서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|충북|충남|전북|전남|"
    r"경북|경남|제주|시도|지역별|지자체")

INTL_VW = {"MT_RTITLE"}          # 국제기구별 통계
REGION_VW = {"MT_GTITLE01"}      # e-지방지표 등 지역지표
DOMESTIC_VW = {"MT_ZTITLE"}      # 주제별 국내 통계


def _covers(row: dict, period: str) -> bool | None:
    """수록기간이 주장 시점을 포함하는가. 정보 없으면 None(판단 보류)."""
    yr = str(period or "")[:4]
    if not yr.isdigit():
        return None
    s, e = str(row.get("STRT_PRD_DE", ""))[:4], str(row.get("END_PRD_DE", ""))[:4]
    if not (s.isdigit() and e.isdigit()):
        return None
    return s <= yr <= e


def score_row(row: dict, sentence: str, period: str = "") -> tuple[float, list[str]]:
    """후보 표의 적합도 점수와 근거. 점수가 높을수록 주장에 맞는 표.

    반환: (점수, 근거 목록) — 근거는 감사 로그·설명에 그대로 쓴다.
    """
    tbl = str(row.get("TBL_NM", ""))
    vw = str(row.get("VW_CD", ""))
    stat = str(row.get("STAT_NM", ""))
    path = str(row.get("MT_ATITLE", ""))
    score, why = 0.0, []

    # ① 국제기구 통계는 국내 주장에 부적합 (IMF·OECD 세계경제전망 등)
    if vw in INTL_VW or "국제기구별" in path:
        score -= 5.0
        why.append("국제기구 통계(국내 주장에 부적합)")
    elif vw in DOMESTIC_VW:
        score += 2.0
        why.append("국내 주제별 통계")

    # ② 지역표 — 주장이 지역을 말할 때만 적합
    claim_region = bool(RE_REGION.search(sentence))
    is_region_tbl = vw in REGION_VW or "(시도" in tbl or "시도/시" in tbl
    if is_region_tbl:
        if claim_region:
            score += 2.0
            why.append("지역 주장 ↔ 지역표 일치")
        else:
            score -= 3.0
            why.append("전국 주장인데 지역표")

    # ③ 주기 정합 — 월간 주장엔 월별 표, 연간 주장엔 연도별 표
    monthly_claim = bool(RE_MONTHLY.search(sentence))
    annual_claim = bool(RE_ANNUAL.search(sentence))
    if monthly_claim:
        if "월별" in tbl:
            score += 4.0
            why.append("월간 주장 ↔ 월별 표 일치")
        elif "연도별" in tbl or "연간" in tbl:
            score -= 3.0
            why.append("월간 주장인데 연도별 표")
    elif annual_claim:
        if "연도별" in tbl or "연간" in tbl:
            score += 3.0
            why.append("연간 주장 ↔ 연도별 표 일치")
        elif "월별" in tbl:
            score -= 1.0
            why.append("연간 주장인데 월별 표")

    # ④ 조사명이 주장에 등장하면 가점 (소비자물가조사 ↔ '소비자물가')
    if stat and stat.replace("조사", "") and stat.replace("조사", "") in sentence:
        score += 1.5
        why.append(f"조사명 정합({stat})")

    # ⑤ 수록기간 커버 — 못 덮으면 조회해도 헛일
    cov = _covers(row, period)
    if cov is False:
        score -= 4.0
        why.append("수록기간이 주장 시점을 못 덮음")
    elif cov is True:
        score += 1.0
        why.append("수록기간 커버")

    return score, why


def rerank_rows(rows: list[dict], sentence: str, period: str = "") -> list[dict]:
    """후보를 적합도 순으로 재정렬. 동점이면 원래 RANK 순서를 유지(안정 정렬).

    각 행에 `_rerank_score`·`_rerank_why`를 붙여 감사 추적에 남긴다.
    """
    scored = []
    for i, r in enumerate(rows):
        s, why = score_row(r, sentence, period)
        r = dict(r)
        r["_rerank_score"] = round(s, 2)
        r["_rerank_why"] = why
        r["_orig_rank"] = i + 1
        scored.append(r)
    return sorted(scored, key=lambda r: (-r["_rerank_score"], r["_orig_rank"]))
