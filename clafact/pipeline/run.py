"""파이프라인 오케스트레이터 — MVP 데모용 E2E 흐름 (LLM·API Key 불필요).

기사 텍스트 → 문장 분리 → 주장 탐지 → 규칙 파싱 → 통계 검색(경로 A)
→ 근거 선택(파생 계산 포함) → 결정적 판정 → 템플릿 설명.

설명은 LLM 대신 템플릿(환각 0 보장). HCX 연동 시 Explainer 로 교체.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from clafact.kosis import KosisClient
from clafact.pipeline import detect
from clafact.pipeline.ingest import split_sentences
from clafact.pipeline.parse import parse_claim, Quantity
from clafact.pipeline.retrieve import StatIndex, TableHit, fetch_evidence
from clafact.pipeline.verdict import compare, derived_ratio, normalize
from clafact.schemas import Evidence

RE_AGE_BAND = re.compile(r"(\d+)\s*[~∼]\s*\d+\s*세|(\d+)\s*세\s*이상")


@dataclass
class ClaimResult:
    sentence: str
    label: str                 # match / mismatch / unverifiable / not_claim
    confidence: str | None = None
    reason: str = ""
    calculation: str = ""
    quantity: str = ""
    period: str = ""
    evidence: dict = field(default_factory=dict)
    explanation: str = ""
    notes: list[str] = field(default_factory=list)


def _pick_quantity(quantities: list[Quantity], sentence: str) -> Quantity:
    """판정 대상 수치 선택: %p(변화폭)보다 %(수준)를, 없으면 첫 번째."""
    pct = [q for q in quantities if q.unit in ("%", "퍼센트")]
    return pct[0] if pct else quantities[0]


def _band_start(c2: str) -> int | None:
    m = RE_AGE_BAND.search(c2)
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def _derived_age_ratio(sentence: str, evs: list[Evidence]) -> tuple[float, str] | None:
    """규칙 A2-0007: 'NN세 이상 비율' 주장은 연령 구간 합산 ÷ 전체(계)로 재현한다."""
    m = re.search(r"(\d+)\s*세\s*이상\s*(?:인구\s*)?비율", sentence)
    if not m:
        return None
    cutoff = int(m.group(1))
    total = next((e for e in evs if e.query_params.get("c2") == "계"), None)
    bands = [e for e in evs
             if (s := _band_start(e.query_params.get("c2", ""))) is not None and s >= cutoff]
    if not total or not bands:
        return None
    ratio = derived_ratio([e.value for e in bands], total.value) * 100
    calc = " + ".join(f"{int(e.value):,}" for e in bands) + f" = {int(sum(e.value for e in bands)):,}"
    calc += f" ÷ {int(total.value):,} = {ratio:.1f}%"
    return ratio, calc


def _pick_c1(evs: list[Evidence], sentence: str) -> list[Evidence]:
    """분류1(C1) 선택: 문장에 등장하는 분류명 우선, 없으면 전체 유지."""
    names = {e.query_params.get("c1", "") for e in evs}
    for name in sorted(names, key=len, reverse=True):
        if name and (name in sentence or name.rstrip("특별시광역시도") in sentence):
            return [e for e in evs if e.query_params.get("c1") == name]
    return evs


def verify_sentence(sentence: str, article_date: str,
                    index: StatIndex, client: KosisClient) -> ClaimResult:
    r = ClaimResult(sentence=sentence, label="not_claim")

    # 1) 탐지
    if not detect.is_candidate(sentence):
        return r

    # 2) 규칙 파싱
    pc = parse_claim(sentence, article_date)
    if not pc.quantities:
        r.label, r.reason = "unverifiable", "수치 미검출 — 정의가 불명확한 주장"
        r.explanation = f'판정: 판단불가. "{sentence}"에서 대조 가능한 수치를 특정할 수 없습니다.'
        return r
    q = _pick_quantity(pc.quantities, sentence)
    r.quantity = f"{q.raw}"
    if pc.period:
        r.period = pc.period
    else:
        r.period = str(article_date)[:4]
        r.notes.append("시점 미명시 — 기사 작성 연도로 가정")
    # 전망형은 검증 제외
    if "전망" in sentence or "예상된다" in sentence:
        r.label, r.reason = "unverifiable", "전망형 주장 — 미래 시점은 검증 불가"
        r.explanation = "판정: 판단불가. 미래 예측은 공식 통계로 검증할 수 없습니다."
        return r

    # 3) 통계표 검색 (경로 A)
    hits = index.search(sentence, top_k=3)
    if not hits:
        r.label, r.reason = "unverifiable", "대응 통계표 검색 실패 (억지 매핑 금지)"
        r.explanation = "판정: 판단불가. 주장에 대응하는 KOSIS 통계표를 찾지 못했습니다. (이 실패는 별칭 사전 확충의 원료가 됩니다)"
        return r
    hit = hits[0]

    # 4) 근거 조회·선택
    evs = _pick_c1(fetch_evidence(client, hit, r.period), sentence)
    if not evs:
        r.label, r.reason = "unverifiable", f"시점({r.period}) 수록 데이터 부재"
        r.explanation = f"판정: 판단불가. {hit.tbl_name}에 {r.period} 시점 자료가 없습니다."
        return r

    claimed_fam = normalize(1, q.composed_unit)[1]
    same_fam = [e for e in evs if normalize(1, e.unit)[1] == claimed_fam]
    derived = None
    if not same_fam and claimed_fam == "percent":
        derived = _derived_age_ratio(sentence, evs)

    if same_fam:
        ev = next((e for e in same_fam if e.query_params.get("c2") == "계"), same_fam[0])
        official, official_unit, calc_note = ev.value, ev.unit, ""
    elif derived:
        ratio, calc_note = derived
        official, official_unit = ratio, "%"
        ev = evs[0]
    else:
        r.label = "unverifiable"
        r.reason = f"단위 대응 불가: 주장 {q.composed_unit or '무단위'} vs 통계 {evs[0].unit}"
        r.explanation = f"판정: 판단불가. {hit.tbl_name}의 단위({evs[0].unit})로는 주장 단위({q.composed_unit})를 검증할 수 없습니다."
        return r

    # 5) 결정적 판정
    res = compare(q.value, q.composed_unit, official, official_unit, op=pc.op)
    v = res.verdict
    r.label, r.confidence = v.label.value, v.confidence
    r.reason, r.calculation = v.reason, (calc_note or v.calculation)
    r.evidence = {"tbl": f"{ev.source_note} ({ev.tbl_id})",
                  "value": f"{official:g}{official_unit}", "period": r.period}

    # 6) 템플릿 설명 (환각 0 — 조회된 값만 사용)
    label_ko = {"match": "일치", "mismatch": "불일치", "unverifiable": "판단불가"}[r.label]
    r.explanation = (
        f"판정: {label_ko}. 기사 주장 [{q.raw}] ↔ 공식 통계 [{official:g}{official_unit}] "
        f"(출처: {ev.source_note}, {r.period} 기준). "
        f"근거: {r.reason}. 계산: {r.calculation}. "
        f"한계: 통계 수록 시점·정의와 기사 서술이 다를 수 있어 최종 판단은 검증자 확인이 필요합니다."
    )
    return r


def verify_article(text: str, article_date: str,
                   index: StatIndex, client: KosisClient) -> list[ClaimResult]:
    return [verify_sentence(s, article_date, index, client)
            for s in split_sentences(text)]
