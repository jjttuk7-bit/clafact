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


def _dim(e: Evidence) -> str:
    """연령 등 세부 차원 값 — 표에 따라 C2(분류) 또는 ITM(항목)에 있다.
    실 KOSIS 검증(2026-07-14): DT_1EA1019 는 연령이 ITM_NM 차원."""
    return e.query_params.get("c2") or e.query_params.get("itm", "")


def _derived_age_ratio(sentence: str, evs: list[Evidence]) -> tuple[float, str] | None:
    """규칙 A2-0007: 'NN세 이상 비율' 주장은 연령 구간 합산 ÷ 전체(계)로 재현한다."""
    m = re.search(r"(\d+)\s*세\s*이상\s*(?:인구\s*)?비율", sentence)
    if not m:
        return None
    cutoff = int(m.group(1))
    total = next((e for e in evs if _dim(e) == "계"), None)
    bands = [e for e in evs
             if (s := _band_start(_dim(e))) is not None and s >= cutoff]
    if not total or not bands:
        return None
    ratio = derived_ratio([e.value for e in bands], total.value) * 100
    calc = " + ".join(f"{int(e.value):,}" for e in bands) + f" = {int(sum(e.value for e in bands)):,}"
    calc += f" ÷ {int(total.value):,} = {ratio:.1f}%"
    return ratio, calc


# 규칙 A2-0009 지표 가드: 증감률을 계산해도 되는 계열인지 문장 단서로 확인.
# 단위가 '가구'인 통계로 '재배면적' 주장을 판정하면 틀린 지표로 오판한다 —
# 지표명 추출(LLM 슬롯)이 붙기 전까지는 보수적으로 스킵한다.
UNIT_TOKENS = {
    "가구": ("가구", "농가", "어가"),
    "명": ("명", "인구", "사람", "출생아", "취업자", "실업자"),
    "원": ("원", "매출", "소득", "가격"),
}


def _metric_guard(sentence: str, unit: str) -> bool:
    tokens = UNIT_TOKENS.get(unit, (unit,) if unit else ())
    return any(t in sentence for t in tokens)


def _yoy_change(sentence: str, cur: list[Evidence], prev: list[Evidence],
                trend: str) -> tuple[float, str, str] | None:
    """규칙 A2-0009: 증감률 주장('전년보다 X% 감소')을 두 시점 원자료로 재현.

    반환: (변화율%, 계산식, 실제 방향 up/down) — 적용 불가면 None.
    """
    if trend not in ("up", "down"):
        return None
    c_total = next((e for e in cur if _dim(e) == "계"), None)
    p_total = next((e for e in prev if _dim(e) == "계"), None)
    if not c_total or not p_total or p_total.value == 0:
        return None
    if not _metric_guard(sentence, c_total.unit):
        return None  # 지표 불일치 가능성 → 억지 판정 금지
    rate = (c_total.value - p_total.value) / p_total.value * 100
    calc = (f"({int(c_total.value):,} − {int(p_total.value):,}) ÷ {int(p_total.value):,}"
            f" = {rate:+.1f}%")
    return rate, calc, ("up" if rate > 0 else "down")


def _pick_c1(evs: list[Evidence], sentence: str) -> list[Evidence]:
    """분류1(C1) 선택: 문장에 등장하는 분류명 우선.

    규칙 A2-0008 (실 API 검증에서 발견): KOSIS 결합 차원은 '차원명 : 값' 접두
    형식을 쓴다 (예: '영농형태 : 과수'). 콜론 뒤 값으로 문장과 매칭해야 한다.
    매칭 실패 시 '전국'(총계)을 우선하고, 그것도 없으면 전체 유지.
    """
    names = {e.query_params.get("c1", "") for e in evs}
    def tail(name: str) -> str:
        return name.split(":")[-1].strip()
    for name in sorted(names, key=lambda n: -len(tail(n))):
        t = tail(name)
        if t and (t in sentence or t.rstrip("특별시광역시도") in sentence):
            return [e for e in evs if e.query_params.get("c1") == name]
    if any(e.query_params.get("c1") == "전국" for e in evs):
        return [e for e in evs if e.query_params.get("c1") == "전국"]
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
    yoy = None
    if not same_fam and claimed_fam == "percent":
        derived = _derived_age_ratio(sentence, evs)
        if not derived:
            # 규칙 A2-0009: 증감률 재현 — 전년도 데이터를 추가 조회
            prev_period = str(int(r.period[:4]) - 1)
            prev = _pick_c1(fetch_evidence(client, hit, prev_period), sentence)
            yoy = _yoy_change(sentence, evs, prev, pc.trend)

    if same_fam:
        ev = next((e for e in same_fam if _dim(e) == "계"), same_fam[0])
        official, official_unit, calc_note = ev.value, ev.unit, ""
    elif derived:
        ratio, calc_note = derived
        official, official_unit = ratio, "%"
        ev = evs[0]
    elif yoy:
        rate, calc_note, actual_dir = yoy
        ev = evs[0]
        if pc.trend != actual_dir:
            # 방향 불일치: 수치 이전에 증감 방향 자체가 틀림 (예: 줄었다는데 실제는 증가)
            dir_ko = {"up": "증가", "down": "감소"}
            r.label, r.confidence = "mismatch", "medium"
            r.reason = f"방향 불일치 — 기사는 {dir_ko[pc.trend]} 주장, 실제는 {dir_ko[actual_dir]} ({rate:+.1f}%)"
            r.calculation = calc_note
            r.evidence = {"tbl": f"{ev.source_note} ({ev.tbl_id})",
                          "value": f"{rate:+.1f}%", "period": f"{r.period} (전년 대비)"}
            r.explanation = (
                f"판정: 불일치. 기사 주장 [{q.raw} {dir_ko[pc.trend]}] ↔ 실제 [전년 대비 {rate:+.1f}% {dir_ko[actual_dir]}] "
                f"(출처: {ev.source_note}, {r.period} vs 전년). 계산: {calc_note}. "
                f"수치 크기 이전에 증감 방향 자체가 통계와 다릅니다. "
                f"한계: 통계 정의와 기사 서술이 다를 수 있어 최종 판단은 검증자 확인이 필요합니다."
            )
            return r
        official, official_unit = abs(rate), "%"
    else:
        r.label = "unverifiable"
        r.reason = f"단위 대응 불가: 주장 {q.composed_unit or '무단위'} vs 통계 {evs[0].unit}"
        r.explanation = f"판정: 판단불가. {hit.tbl_name}의 단위({evs[0].unit})로는 주장 단위({q.composed_unit})를 검증할 수 없습니다."
        return r

    # 5) 결정적 판정
    res = compare(q.value, q.composed_unit, official, official_unit, op=pc.op)
    v = res.verdict
    r.label, r.confidence = v.label.value, v.confidence
    # 규칙 A2-0004: 파생 계산(비율·증감률 재현)을 경유한 판정은 medium 이하 — 리뷰 우선
    if (derived or yoy) and r.confidence == "high":
        r.confidence = "medium"
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
