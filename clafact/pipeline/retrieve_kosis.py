"""경로 C — KOSIS 통합검색 기반 매핑 (구현/검색매핑_구현가이드 Step 4).

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


def search_kosis(query: str, client, *, period: str = "", top_k: int = 10,
                 sentence: str = "") -> list[TableHit]:
    """통합검색으로 통계표 후보를 뽑는다.

    - RANK 순서를 rank 기반 score(1/순위)로 환산해 하류(RRF·정렬)와 호환.
    - period 가 주어지면 수록기간이 안 맞는 표를 조회 전에 제거.
    - sentence 가 주어지면 **재순위**한다(rerank.py) — RANK 1위가 주장에 맞는
      표라는 보장이 없기 때문. 추가 호출 없이 검색 응답 메타만으로 판단한다.
    """
    rows = client.integrated_search(searchNm=query, sort="RANK", resultCount=top_k)
    if sentence:
        from clafact.pipeline.rerank import rerank_rows
        rows = rerank_rows(rows, sentence, period)
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


class KosisSearchIndex:
    """StatIndex 인터페이스를 **실 KOSIS 통합검색**으로 구현한 어댑터 (경로 C).

    `verify_sentence(sentence, date, index, client)` 의 index 자리에 이걸 넣으면
    픽스처 인덱스 대신 실 KOSIS 28만 표를 검색해 판정 파이프라인이 그대로 돈다.
    (StatIndex 와 같은 `search(query, top_k) -> list[TableHit]` 계약을 만족)

    질의는 주장 문장 전체가 아니라 **매칭 지표어**를 쓴다 — 실측상 KOSIS 통합검색은
    검색창처럼 짧은 키워드를 기대하기 때문(긴 문장 질의는 err30). 상세는
    `source_classify.kosis_query` 주석 참조.
    """

    def __init__(self, client, period: str = ""):
        self.client = client
        self.period = period
        self.last_query = ""       # 감사·디버깅용: 실제로 던진 검색어

    def search(self, query: str, top_k: int = 3) -> list[TableHit]:
        from clafact.pipeline.source_classify import kosis_query
        q = kosis_query(query)
        self.last_query = q
        if not q:
            return []              # 지표어 없음 → 억지 매핑 대신 빈 결과(판단불가로 흐른다)
        # 검색은 짧은 지표어로, 재순위는 주장 문장 전체로 — 검색과 선택의 역할 분리.
        # 검색어에서 버린 정보(주기·지역·모집단)가 여기서 표 선택에 쓰인다.
        return search_kosis(q, self.client, period=self.period,
                            top_k=max(top_k, 10), sentence=query)[:top_k]
