"""파이프라인 오케스트레이터 — MVP 데모용 E2E 흐름 (LLM·API Key 불필요).

기사 텍스트 → 문장 분리 → 주장 탐지 → 규칙 파싱 → 통계 검색(경로 A)
→ 근거 선택(파생 계산 포함) → 결정적 판정 → 템플릿 설명.

설명은 LLM 대신 템플릿(환각 0 보장). HCX 연동 시 Explainer 로 교체.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from clafact import audit
from clafact.kosis import KosisClient
from clafact.pipeline import detect
from clafact.pipeline.ingest import split_sentences
from clafact.pipeline.parse import parse_claim, Quantity, _to_date
from clafact.pipeline.retrieve import StatIndex, TableHit, fetch_evidence
from clafact.pipeline.verdict import compare, derived_ratio, normalize
from clafact.schemas import Evidence

RE_AGE_BAND = re.compile(r"(\d+)\s*[~∼]\s*\d+\s*세|(\d+)\s*세\s*이상")

# 규칙 A2-0013: 지수 기준연도 (문서 19 §7.3)
RE_INDEX_BASE = re.compile(r"(\d{4})\s*[=＝]\s*100")   # 통계표명 "(2020=100)" 에서 기준연도
RE_RATE_WORD = re.compile(r"상승률|증가율|하락률|감소율|상승|하락|올랐|내렸|증가|감소")


def _index_base_year(tbl_name: str) -> str | None:
    """지수 통계표명에서 기준연도 추출. '소비자물가지수(2020=100)' → '2020'."""
    if "지수" not in (tbl_name or ""):
        return None
    m = RE_INDEX_BASE.search(tbl_name)
    return m.group(1) if m else None


def _is_index_level_claim(sentence: str, q) -> bool:
    """지수 '수준' 주장인가(기준연도 의존) vs 상승률·증감률(기준연도 불변).

    - 상승률/증감률(% + 추세어)은 기준연도가 달라도 같으므로 회피 대상 아님.
    - 지수 수준(예: '지수 114.2')은 기준연도에 따라 값이 달라져 직접 대조 불가.
    """
    is_rate = q.unit in ("%", "%p", "퍼센트") and bool(RE_RATE_WORD.search(sentence))
    if is_rate:
        return False
    return "지수" in sentence


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
    # 감사 추적 (문서 20 기능 3) — "이 판정을 어떻게 재현하는가".
    # 예전에는 evidence 를 {tbl,value,period} 로 요약하며 org_id·조회 파라미터를
    # 통째로 버렸다. 그러면 재현이 불가능하다.
    audit: dict = field(default_factory=dict)


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


# 주장이 말하는 '비교 기준'과 통계표 항목(ITM)을 맞춘다.
# 실측(2026-07-20): '전년 동월 대비 2.2%' 주장에 전월비(0.7%)를 가져와 오'불일치'.
# 같은 표·같은 시점이라도 항목이 다르면 완전히 다른 수치다.
# 순서 주의 — '전년 동월'을 '전월'보다 먼저 본다.
BASIS_PATTERNS = [
    (re.compile(r"전년\s*동월|작년\s*같은\s*달|지난해\s*같은\s*달"), "전년동월"),
    (re.compile(r"전년\s*누계|누계\s*대비"), "전년누계"),
    (re.compile(r"전월\s*대비|전달\s*(?:대비|보다)|전월비"), "전월"),
    (re.compile(r"전년\s*대비|지난해\s*대비|작년보다|지난해보다|전년비"), "전년"),
]


RE_RATE_CLAIM = re.compile(r"상승률|등락률|증감률|올랐|내렸|떨어졌|상승|하락")


def _claim_basis(sentence: str, period: str = "") -> str:
    """주장이 명시한 비교 기준 ('전년동월'/'전월'/'전년누계'/'전년'). 없으면 ''.

    명시가 없어도 물가 '상승률' 주장은 관례상 전년 대비다 — 월 시점이면 전년동월비,
    연 시점이면 전년비. ('작년 8월(2%) 이후 5개월 만' 처럼 기준을 안 밝힌 주장에
    전월비를 집어 오'불일치'가 났다 — 실측 2026-07-20.)
    """
    for rx, key in BASIS_PATTERNS:
        if rx.search(sentence or ""):
            return key
    if RE_RATE_CLAIM.search(sentence or ""):
        return "전년동월" if len(str(period).replace("-", "")) >= 6 else "전년"
    return ""


def _pick_basis(evs: list[Evidence], basis: str) -> list[Evidence]:
    """항목(ITM)이 주장의 비교 기준과 같은 근거만 남긴다. 없으면 빈 리스트."""
    if not basis:
        return evs
    return [e for e in evs
            if basis in str(e.query_params.get("itm", "")).replace(" ", "")]


def _prefer_total_index(evs: list[Evidence], sentence: str) -> list[Evidence]:
    """지수종류가 여러 개인 표에서 주장이 특정하지 않으면 '총지수'를 쓴다.

    '소비자물가가 2.2% 올랐다'는 총지수를 말한다 — 생활물가지수·신선식품지수는
    기사가 그 이름을 직접 부를 때만 대상이다.
    """
    named = ("생활물가", "신선식품", "식료품", "에너지", "농산물", "근원")
    if any(n in (sentence or "") for n in named):
        return evs
    total = [e for e in evs
             if "총지수" in str(e.query_params.get("c1", ""))
             or "총지수" in str(e.query_params.get("itm", ""))]
    return total or evs


RE_MONTHLY_CLAIM = re.compile(
    r"지난달|전월|이달|당월|전년\s*동월|작년\s*같은\s*달|\d{1,2}월\b|월간|월별")


def _granularity_mismatch(sentence: str, evs: list[Evidence]) -> str | None:
    """규칙 A2-0015: 주장과 근거의 시점 입도가 다르면 대조하지 않는다.

    월 단위 주장(‘지난달 … 전년 동월 대비 2.2%’)을 연 단위 통계(연간 2.3%)와
    비교하면 값이 당연히 어긋나 '정확하게 틀린' 불일치가 나온다. 실측(2026-07-20
    첫 실판정)에서 오'불일치' 4건 중 3건이 이 유형이었다.

    판별: 주장에 월 표지가 있는데 근거의 수록시점(PRD_DE)이 연 단위(YYYY, 4자리)면
    입도 불일치. 반환값은 회피 사유 표기용 문자열.
    """
    if not RE_MONTHLY_CLAIM.search(sentence or ""):
        return None
    for e in evs:
        prd = str(e.period or "")
        if len(prd) >= 6 and prd[:6].isdigit():
            return None          # 월 단위 근거가 하나라도 있으면 대조 가능
    prds = {str(e.period) for e in evs if e.period}
    return f"주장은 월 단위, 근거는 연 단위({', '.join(sorted(prds)) or '연간'})"


def _provisional_stale(evs: list[Evidence], article_date) -> str | None:
    """규칙 A2-0012: 통계가 기사 작성 이후 갱신됐으면 당시 공표값(잠정치)을 알 수 없다.

    LST_CHN_DE(최종수정일) > 기사 작성일이면, 반환값은 그 최종수정일(회피 사유 표기용).
    KOSIS 는 과거 공표값(vintage)을 제공하지 않으므로(문서 19 §7.1), 현재 확정값으로
    '불일치' 판정하면 우리가 틀린다 — 정직하게 판단불가로 회피한다.

    필드가 없으면 적용하지 않는다. 실 API 는 항상 LST_CHN_DE 를 주므로, 필드 부재는
    수기 픽스처 등 예외 상황뿐 — 없는 근거로 회피를 남발하지 않는다.
    """
    try:
        adate = _to_date(article_date)
    except (ValueError, TypeError):
        return None
    latest = ""
    for e in evs:
        d = (e.last_change_date or "").strip()
        if d and d > latest:      # ISO(YYYY-MM-DD) 문자열은 사전순=시간순
            latest = d
    if not latest:
        return None
    try:
        return latest if _to_date(latest) > adate else None
    except (ValueError, TypeError):
        return None


def _mk_audit(client: KosisClient, hit: TableHit, evs: list[Evidence],
              period: str, rules: list[str]) -> dict:
    """판정에 실제로 쓰인 것만 담는다 — 조회했으나 안 쓴 행까지 넣으면 감사가 흐려진다."""
    rows = [{"c1": e.query_params.get("c1", ""), "c2": e.query_params.get("c2", ""),
             "itm": e.query_params.get("itm", ""), "unit": e.unit,
             "period": e.period, "value": e.value} for e in evs]
    return audit.build(
        engine_name=type(client).__name__,
        org_id=hit.org_id, tbl_id=hit.tbl_id, tbl_name=hit.tbl_name,
        params={"prd_de": period, "prd_se": "Y", "itm_id": "ALL", "obj_l1": "ALL"},
        rows=rows, rules=rules, match_score=hit.score,
    ).as_dict()


def verify_sentence(sentence: str, article_date: str,
                    index: StatIndex, client: KosisClient) -> ClaimResult:
    r = ClaimResult(sentence=sentence, label="not_claim")
    rules: list[str] = []   # 이 판정에 적용된 규칙 카드 — 감사 추적의 핵심

    # 1) 탐지
    if not detect.is_candidate(sentence):
        return r
    if mixed_reason := detect.mixed_claim_reason(sentence):
        r.label, r.reason = "unverifiable", mixed_reason
        r.explanation = "판정: 판단불가. 여러 기사 제목·수치가 섞인 문장은 자동 통계 검증하지 않습니다."
        return r
    if (rid := detect.which_rule(sentence)):
        rules.append(rid)  # 규칙 카드에서 온 탐지 패턴이 잡은 경우

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

    # 규칙 A2-0016: 주장이 명시한 비교 기준(전년동월비 등)과 같은 항목만 대조한다.
    # 같은 표·같은 시점이라도 항목이 다르면 다른 수치다 — 기준을 못 맞추면 판정하지 않는다.
    basis = _claim_basis(sentence, r.period)
    if basis:
        matched = _pick_basis(evs, basis)
        # 기준 항목이 아예 없는 표(단일 항목 표 등)라면 원래 근거를 그대로 쓴다.
        # 여러 기준이 공존하는 표에서만 '못 고르면 회피'가 의미 있다.
        multi_basis = len({str(e.query_params.get("itm", "")) for e in evs}) > 1
        if not matched and not multi_basis:
            matched, basis = evs, ""
        if not matched:
            rules.append("A2-0016")
            r.label, r.reason = "unverifiable", f"비교 기준({basis}비) 항목 부재"
            r.explanation = (
                f"판정: 판단불가. 기사는 '{basis} 대비' 수치를 말하는데, "
                f"{hit.tbl_name}에서 해당 항목을 찾지 못했습니다. 기준이 다른 항목"
                f"(예: 전월비)과 대조하면 값이 어긋나는 것이 당연하므로 판정하지 않습니다."
            )
            r.audit = _mk_audit(client, hit, evs, r.period, rules)
            return r
        rules.append("A2-0016")
        evs = matched
    evs = _prefer_total_index(evs, sentence)

    # 규칙 A2-0015: 주장(월 단위)과 근거(연 단위)의 시점 입도가 다르면 대조 불가
    gran = _granularity_mismatch(sentence, evs)
    if gran:
        rules.append("A2-0015")
        r.label, r.reason = "unverifiable", f"시점 입도 불일치 — {gran}"
        r.explanation = (
            f"판정: 판단불가. 기사 주장은 월 단위 수치인데 대응 통계는 연 단위입니다"
            f"({gran}). 입도가 다른 값을 직접 대조하면 어긋나는 것이 당연하므로 "
            f"'불일치'로 판정하지 않습니다. 월 단위 통계표를 찾으면 검증 가능합니다."
        )
        r.audit = _mk_audit(client, hit, evs, r.period, rules)
        return r

    # 규칙 A2-0012: 기사 작성 이후 통계가 갱신됐으면 당시 잠정치를 알 수 없다 → 판단불가
    stale = _provisional_stale(evs, article_date)
    if stale:
        rules.append("A2-0012")
        r.label, r.reason = "unverifiable", f"기사 작성 이후 통계 갱신 (최종수정일 {stale})"
        r.explanation = (
            f"판정: 판단불가. 이 통계는 기사 작성일({str(article_date)[:10]}) 이후에 "
            f"수정되었습니다(최종수정일 {stale}). 기사가 인용한 당시 공표값(잠정치)을 "
            f"본 시스템이 확인할 수 없으므로 판정하지 않습니다. 현재 값으로 '불일치'로 "
            f"판정하는 것은 부당합니다. (KOSIS는 과거 공표값을 제공하지 않습니다)"
        )
        r.audit = _mk_audit(client, hit, evs, r.period, rules)
        return r

    # 규칙 A2-0013: 지수(index) 수준 주장은 기준연도가 맞아야 비교 가능. 확인 불가 → 판단불가
    base_year = _index_base_year(hit.tbl_name)
    if base_year and _is_index_level_claim(sentence, q):
        rules.append("A2-0013")
        r.label, r.reason = "unverifiable", f"지수 기준연도({base_year}=100) 정합 확인 불가"
        r.explanation = (
            f"판정: 판단불가. 지수(index)는 기준연도에 따라 값이 달라집니다 "
            f"(이 통계는 {base_year}=100 기준). 기사가 어느 기준연도 계열의 지수를 "
            f"인용했는지 확인할 수 없어 지수 수준({q.raw})을 직접 대조하지 않습니다. "
            f"(상승률·증감률 주장은 기준연도와 무관하므로 이 회피 대상이 아닙니다.)"
        )
        r.audit = _mk_audit(client, hit, evs, r.period, rules)
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
        rules.append("A2-0007")  # 연령 구간 합산 ÷ 전체 파생 계산
    elif yoy:
        rate, calc_note, actual_dir = yoy
        ev = evs[0]
        rules.append("A2-0009")  # 증감률 재현
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
            r.audit = _mk_audit(client, hit, evs, r.period, rules)
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
    if pc.op in ("gte", "lte"):
        rules.append("A2-0001")  # 임계 표현의 부등호 판정
    # 규칙 A2-0004: 파생 계산(비율·증감률 재현)을 경유한 판정은 medium 이하 — 리뷰 우선
    if (derived or yoy) and r.confidence == "high":
        r.confidence = "medium"
        rules.append("A2-0004")
    r.reason, r.calculation = v.reason, (calc_note or v.calculation)
    r.evidence = {"tbl": f"{ev.source_note} ({ev.tbl_id})",
                  "value": f"{official:g}{official_unit}", "period": r.period}
    r.audit = _mk_audit(client, hit, evs, r.period, rules)

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
