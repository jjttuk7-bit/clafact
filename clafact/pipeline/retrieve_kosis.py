"""경로 C — KOSIS 통합검색 기반 매핑 (docs/검색매핑_구현가이드 Step 4).

인덱싱 0: 우리가 28만 표를 인덱싱하지 않고 KOSIS 검색엔진에 검색어를 던진다.
전수 인덱싱은 호출 예산상 불가능(28만 표 vs 1,000회 = 289배, 문서 19 §5.3)하므로,
전수 커버리지를 얻는 유일하게 현실적인 길이다 (주장당 1회 호출).

입력: 검색어(query_gen.make_query 로 생성) → 출력: list[TableHit] (경로 A/B 와 동일 계약).
클라이언트는 KosisClient 프로토콜 — 오프라인 FixtureKosisClient / 실 HttpKosisClient 스위치.
"""
from __future__ import annotations

from clafact.pipeline.retrieve import TableHit


def _covers_period(row: dict, period: str) -> bool:
    """통계표 수록기간(STRT~END_PRD_DE)이 기사 시점을 포함하는가.

    포함 안 하면 조회해도 헛일이므로 후보에서 제거 → 예산 절감 (문서 19 §4.6).
    수록기간 정보가 없으면(빈 값) 판단 불가 → **포함으로 간주**(못 재는 걸로 후보를
    버리지 않는다 — A2-0012 와 같은 보수적 원칙).
    """
    if not period:
        return True
    yr = str(period)[:4]
    if not yr.isdigit():
        return True
    strt = str(row.get("STRT_PRD_DE", ""))[:4]
    end = str(row.get("END_PRD_DE", ""))[:4]
    if not strt or not end or not strt.isdigit() or not end.isdigit():
        return True
    return strt <= yr <= end


def search_kosis(query: str, client, *, period: str = "", top_k: int = 10) -> list[TableHit]:
    """통합검색으로 통계표 후보를 뽑는다.

    - RANK 순서를 rank 기반 score(1/순위)로 환산해 하류(RRF·정렬)와 호환.
    - period 가 주어지면 수록기간이 안 맞는 표를 조회 전에 제거.
    """
    rows = client.integrated_search(searchNm=query, sort="RANK", resultCount=top_k)
    hits: list[TableHit] = []
    for i, r in enumerate(rows):
        if period and not _covers_period(r, period):
            continue
        tbl_id = r.get("TBL_ID", "")
        if not tbl_id:
            continue
        hits.append(TableHit(
            tbl_id=tbl_id,
            org_id=r.get("ORG_ID", ""),
            tbl_name=r.get("TBL_NM", ""),
            survey=r.get("STAT_NM", ""),
            score=round(1.0 / (i + 1), 4),   # RANK 순위 → 점수
        ))
    return hits[:top_k]
