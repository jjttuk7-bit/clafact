"""KOSIS Retriever — 경로 A 기준선: 별칭 사전 + 키워드 검색 (문서 12 §4 확률적 계획).

플레이북 기술 계단 원칙: 임베딩(경로 B)은 이 기준선을 이겨야만 채택된다.
검색 실패는 곧 판단불가 — 실패 사례가 A1 별칭 사전의 원료가 된다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from clafact.assets.alias_dict import AliasDict
from clafact.kosis import KosisClient
from clafact.schemas import Evidence

RE_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")


def _tokens(text: str) -> set[str]:
    """공백·조사 무시 토큰화: 단어 + 한글 2-gram (형태소 분석기 없이 재현율 확보)."""
    words = RE_TOKEN.findall(text)
    grams: set[str] = set()
    for w in words:
        grams.add(w)
        for i in range(len(w) - 1):
            grams.add(w[i:i + 2])
    return grams


@dataclass
class TableHit:
    tbl_id: str
    org_id: str
    tbl_name: str
    survey: str
    score: float


class StatIndex:
    """통계표 메타 키워드 인덱스 (경로 A).

    실 운영: 통계목록·메타정보 API 로 구축 → 지금은 픽스처 메타로 동일 구조 검증.
    """

    def __init__(self, meta_path: str | Path = "data/samples/kosis/tables_meta.json",
                 aliases: AliasDict | None = None):
        # 규칙 A2-0010: `aliases or AliasDict()` 는 빈 사전(len 0=falsy)을 명시적으로
        # 주입해도 무시하고 기본 사전을 로드하는 버그 — is None 으로 판별해야 한다.
        self.aliases = aliases if aliases is not None else AliasDict()
        self.tables = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        for t in self.tables:
            t["_tokens"] = _tokens(f"{t['TBL_NM']} {t['SURVEY']} {t.get('KEYWORDS', '')}")

    def search(self, query: str, top_k: int = 3) -> list[TableHit]:
        """별칭 치환 → 토큰 겹침 점수(자카드 유사) → Top-k."""
        q = _tokens(self.aliases.substitute(query))
        hits = []
        for t in self.tables:
            inter = len(q & t["_tokens"])
            if inter == 0:
                continue
            score = inter / (len(q | t["_tokens"]) ** 0.5)  # 짧은 질의 편향 완화
            hits.append(TableHit(t["TBL_ID"], t["ORG_ID"], t["TBL_NM"], t["SURVEY"], round(score, 4)))
        return sorted(hits, key=lambda h: -h.score)[:top_k]


RE_PCT_IN_NAME = re.compile(r"\(\s*%\s*\)|비율|구성비|등락률|상승률|증감률")


def _infer_unit(itm_nm: str, tbl_nm: str) -> str:
    """단위 필드가 빈 경우 항목명·통계표명에서 단위를 유추한다.

    KOSIS 등락률 표는 단위를 별도 필드가 아니라 항목명에 넣는다:
    '전년동월비(%)', '전년누계비(%)'. 이때 UNIT_NM 은 빈 문자열이다.
    유추 실패 시 빈 문자열을 그대로 돌려준다(없는 단위를 지어내지 않는다).
    """
    name = f"{itm_nm} {tbl_nm}"
    if RE_PCT_IN_NAME.search(name):
        return "%"
    if itm_nm.endswith(("비", "률", "율")):
        return "%"
    return ""


def fetch_evidence(client: KosisClient, hit: TableHit, period: str,
                   c1: str = "", c2: str = "", itm: str = "") -> list[Evidence]:
    """선택된 통계표에서 근거 수치 조회. 분류(C1/C2)·항목(ITM) 필터는 부분 일치.

    주기(prdSe)는 시점 형식에서 유도한다 — 'YYYY-MM'이면 월(M), 'YYYY-Qn'이면 분기(Q),
    아니면 연(Y). 주기를 연으로 고정하면 월별 통계표에서 자료를 못 받는다
    (실측 2026-07-20: '월별 소비자물가 등락률'에 prdSe=Y로 조회해 전부 자료 없음).
    월 조회는 최근 24개월을 받아 클라이언트에서 해당 월을 고른다.
    """
    p = str(period or "")
    if "Q" in p.upper():
        prd_se, recent = "Q", 8
    elif len(p.replace("-", "")) >= 6:
        prd_se, recent = "M", 24
    else:
        prd_se, recent = "Y", 5
    rows = client.fetch_data(hit.org_id, hit.tbl_id, prd_de=period,
                             prd_se=prd_se, recent_n=recent)
    out = []
    for r in rows:
        if c1 and c1 not in r.get("C1_NM", ""):
            continue
        if c2 and c2 not in r.get("C2_NM", ""):
            continue
        if itm and itm not in r.get("ITM_NM", ""):
            continue
        try:
            value = float(str(r["DT"]).replace(",", ""))
        except (KeyError, ValueError):
            continue  # 결측(-, X 등) → 스킵, 전량 결측이면 상위에서 판단불가
        # 단위가 빈 경우 항목명에서 유추한다 — KOSIS 등락률 표는 단위를 항목명에
        # 넣는다('전년동월비(%)'). UNIT_NM 이 비어 있다고 판정을 포기하면
        # 정작 맞는 근거를 손에 쥐고도 판단불가가 난다 (실측 2026-07-20).
        unit = r.get("UNIT_NM", "") or _infer_unit(r.get("ITM_NM", ""), hit.tbl_name)
        out.append(Evidence(
            tbl_id=hit.tbl_id, org_id=hit.org_id, tbl_name=r.get("TBL_NM", hit.tbl_name),
            query_params={"prd_de": period, "c1": c1 or r.get("C1_NM", ""),
                          "c2": r.get("C2_NM", ""), "itm": r.get("ITM_NM", "")},
            value=value, unit=unit, period=r.get("PRD_DE", period),
            source_note=f"KOSIS {hit.survey} > {hit.tbl_name}",
            last_change_date=r.get("LST_CHN_DE", ""),  # A2-0012 근거 (실 API 는 항상 제공)
        ))
    return out
