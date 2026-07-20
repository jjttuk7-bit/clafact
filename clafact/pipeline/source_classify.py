"""Source Classification (FR — 신규 레이어).

경제면 수치 Claim을 KOSIS로 보내도 되는 것과 안 되는 것으로 먼저 나눈다.
기획 문서(ClaFact_Source_Classification_기획): 규칙 v0.1 키워드 사전 1차 분류.
2단계(KOSIS 통합검색 확인 신호, 경로 C)는 W1에서 결합 — 여기는 규칙만.

핵심 원칙: **KOSIS_precision 최우선**. KOSIS가 아닌 Claim을 억지로 KOSIS에
매핑하지 않는다. 충돌 시 비-KOSIS 우승, 애매하면 UNKNOWN(사람 검토 큐).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_ROUTING_PATH = Path(__file__).resolve().parents[2] / "data/assets/routing_v01.json"

# source_type 8종 (기획 문서 §2)
KOSIS_DOMESTIC = "KOSIS_DOMESTIC"
KOSIS_BUT_COMPLEX = "KOSIS_BUT_COMPLEX"
OTHER_OFFICIAL = "OTHER_OFFICIAL"
PRIVATE_SOURCE = "PRIVATE_SOURCE"
PLATFORM_SOURCE = "PLATFORM_SOURCE"
FORECAST_OR_OPINION = "FORECAST_OR_OPINION"
UNKNOWN = "UNKNOWN"

# route (기획 문서 §5 출력 예시)
ROUTE = {
    KOSIS_DOMESTIC: "KOSIS_RETRIEVAL",
    KOSIS_BUT_COMPLEX: "KOSIS_RETRIEVAL",
    OTHER_OFFICIAL: "NON_KOSIS_QUEUE",
    PRIVATE_SOURCE: "NON_KOSIS_QUEUE",
    PLATFORM_SOURCE: "NON_KOSIS_QUEUE",
    FORECAST_OR_OPINION: "OUT_OF_SCOPE",
    UNKNOWN: "HUMAN_REVIEW",
}


@dataclass
class SourceLabel:
    source_type: str
    domain: str          # 매칭된 도메인 키 ("-" 없음)
    claim_type: str      # 규모형/증감형/파생계산형/전망형/임계형/순위형
    route: str
    confidence: float
    reason: str
    matched_keyword: str = ""   # 분류를 발동시킨 지표어 — KOSIS 검색 질의의 씨앗

    def as_dict(self) -> dict:
        return {
            "source_type": self.source_type, "domain": self.domain,
            "claim_type": self.claim_type, "route": self.route,
            "confidence": self.confidence, "reason": self.reason,
            "matched_keyword": self.matched_keyword,
        }


@lru_cache(maxsize=1)
def _routing(path: str | None = None) -> dict:
    p = Path(path) if path else _ROUTING_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    # 정규식은 미리 컴파일
    data["_ct_compiled"] = {
        k: re.compile(v) for k, v in data["claim_type_patterns"].items()
    }
    return data


def reload_routing() -> None:
    """라우팅 사전 갱신 후 캐시 무효화 (테스트·운영에서 사전 교체 시)."""
    _routing.cache_clear()


def claim_type(sentence: str, cfg: dict | None = None) -> str:
    cfg = cfg or _routing()
    ct = cfg["_ct_compiled"]
    if ct["forecast"].search(sentence):
        return "전망형"
    if ct["threshold"].search(sentence):
        return "임계형"
    if ct["derivation"].search(sentence):
        return "파생계산형"
    if ct["delta"].search(sentence):
        return "증감형"
    if ct["rank"].search(sentence):
        return "순위형"
    return "규모형"


def _match_domain(sentence: str, group: dict) -> tuple[str, str] | None:
    """(도메인, 매칭된 키워드) — 키워드는 KOSIS 검색 질의로 재사용된다.

    가장 긴 키워드 우선: '소비자물가'가 '물가가'보다 구체적이므로 먼저 잡는다.
    """
    best = None
    for dom, kws in group.items():
        for kw in kws:
            if kw in sentence and (best is None or len(kw) > len(best[1])):
                best = (dom, kw)
    return best


def classify(sentence: str, cfg: dict | None = None) -> SourceLabel:
    """단일 문장을 source_type으로 분류. Claim 단위(기사 단위 아님)."""
    cfg = cfg or _routing()
    ct = claim_type(sentence, cfg)

    # 전망·의견은 현재 통계로 검증 부적합 — 최우선 컷
    if ct == "전망형":
        return SourceLabel(FORECAST_OR_OPINION, "-", ct, ROUTE[FORECAST_OR_OPINION],
                           0.75, "전망·예측 표현 — 현재 공식 통계로 검증 부적합")

    # 비-KOSIS 우승 순서 (KOSIS_precision 보호): platform > private > other > kosis
    if (m := _match_domain(sentence, cfg["platform_source"])):
        return SourceLabel(PLATFORM_SOURCE, m[0], ct, ROUTE[PLATFORM_SOURCE],
                           0.7, "플랫폼 수치(조회수·시청률 등) — KOSIS 범위 밖", m[1])
    if (m := _match_domain(sentence, cfg["private_source"])):
        return SourceLabel(PRIVATE_SOURCE, m[0], ct, ROUTE[PRIVATE_SOURCE],
                           0.7, "기업·시장 자료 — KOSIS 범위 밖", m[1])
    if (m := _match_domain(sentence, cfg["other_official"])):
        return SourceLabel(OTHER_OFFICIAL, m[0], ct, ROUTE[OTHER_OFFICIAL],
                           0.7, "비-KOSIS 공식자료(한국은행·부동산원·관세청 등) 가능성", m[1])
    if (m := _match_domain(sentence, cfg["kosis_domestic"])):
        d, kw = m
        complex_ = d in cfg["complex_domains"] or ct in _complex_claim_labels(cfg)
        if complex_:
            return SourceLabel(KOSIS_BUT_COMPLEX, d, ct, ROUTE[KOSIS_BUT_COMPLEX],
                               0.8, "KOSIS 가능하나 파생계산·기준연도·시점/모집단 정렬 필요", kw)
        return SourceLabel(KOSIS_DOMESTIC, d, ct, ROUTE[KOSIS_DOMESTIC],
                           0.85, "KOSIS 국내통계에서 직접 조회 가능한 지표", kw)

    return SourceLabel(UNKNOWN, "-", ct, ROUTE[UNKNOWN],
                       0.3, "규칙 v0.1 사전 밖 — 사람 검토·사전 확장 대상")


_CT_LABEL = {"derivation": "파생계산형", "delta": "증감형", "threshold": "임계형"}


def _complex_claim_labels(cfg: dict) -> set[str]:
    return {_CT_LABEL[k] for k in cfg["complex_claim_types"] if k in _CT_LABEL}


def kosis_query(sentence: str, cfg: dict | None = None) -> str:
    """KOSIS 통합검색용 **짧은** 질의 — 매칭된 지표어를 그대로 쓴다.

    실측 근거(2026-07-20, NCP 서버 30건 배치): KOSIS 통합검색은 검색창처럼
    짧은 키워드를 기대한다. 문장의 잔여 토큰을 이어붙인 긴 질의는
    `err 30 데이터가 존재하지 않습니다`로 27/30 실패했고, '실업률'·'소비자물'
    같은 짧은 질의만 10건씩 반환했다. 그래서 지표어 하나로 검색한다.
    (로컬 픽스처 인덱스는 토큰 OR 매칭이라 긴 질의도 통했다 — 실 API와 다름.)
    """
    label = classify(sentence, cfg)
    return label.matched_keyword


def _is_kosis(label: str) -> bool:
    return label in (KOSIS_DOMESTIC, KOSIS_BUT_COMPLEX)


def routing_metrics(pairs: list[tuple[str, str]]) -> dict:
    """(예측, 정답) 쌍에서 G-SOURCE-1 지표 계산.

    KOSIS_precision 이 최우선 지표(기획 문서 §6):
    KOSIS로 보낸 것 중 실제 KOSIS 정답 비율. 억지 매핑을 벌한다.
    """
    if not pairs:
        return {"n": 0}
    n = len(pairs)
    acc = sum(1 for p, g in pairs if p == g) / n
    # KOSIS_DOMESTIC + KOSIS_BUT_COMPLEX를 한 덩어리로 본 이진 정밀/재현
    tp = sum(1 for p, g in pairs if _is_kosis(p) and _is_kosis(g))
    fp = sum(1 for p, g in pairs if _is_kosis(p) and not _is_kosis(g))
    fn = sum(1 for p, g in pairs if not _is_kosis(p) and _is_kosis(g))
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    unknown_rate = sum(1 for p, _ in pairs if p == UNKNOWN) / n
    return {
        "n": n, "source_type_accuracy": round(acc, 4),
        "kosis_precision": round(prec, 4), "kosis_recall": round(rec, 4),
        "unknown_rate": round(unknown_rate, 4),
    }
