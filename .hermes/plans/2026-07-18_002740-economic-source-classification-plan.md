# Economic News Source Classification Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 2025년 조선일보 경제면 기사 속 수치 Claim을 KOSIS 국내통계 기반 검증 가능 Claim과 KOSIS 외부 자료 Claim으로 자동 분류하는 파이프라인을 설계·구현한다.

**Architecture:** Claim 추출 뒤 곧바로 Verdict로 가지 않고, `source_type` 분류 단계를 추가한다. 규칙 기반 1차 분류 + KOSIS 통합검색 경로 C + 도메인별 출처 사전을 결합해 `KOSIS_DOMESTIC / OTHER_OFFICIAL / PRIVATE_SOURCE / PLATFORM_SOURCE / FORECAST_OR_OPINION / NOISE`로 나눈다.

**Tech Stack:** Python stdlib 우선, 기존 `clafact/pipeline/detect.py`, `parse.py`, `retrieve.py`, `kosis.py`, `eval/harness.py` 재사용. 실 KOSIS 통합검색은 클라우드/브라우저 경로에서만 검증한다.

---

## 1. Current Context / Assumptions

- 2025년 조선일보 1년치 원본 데이터셋은 아직 저장소에 없음.
- 현재 샘플에는 경제/사회 기사 일부와 골든셋 v0 12건이 있음.
- ClaFact 1차 PoC의 근거원은 KOSIS 국내 공식 통계다.
- 경제면에는 KOSIS 외 자료가 많이 섞인다: ECOS, 한국부동산원/국토부, 관세청, 금융감독원, 한국거래소, 기업 공시, 민간 리서치 등.
- 목표는 모든 수치를 바로 검증하는 것이 아니라, 먼저 “KOSIS로 갈 Claim인지 아닌지”를 자동 라우팅하는 것이다.

---

## 2. Proposed Classification Schema

### 2.1 Source Type

```text
KOSIS_DOMESTIC      국내 KOSIS 공식 통계로 검증 가능성이 높음
KOSIS_BUT_COMPLEX   KOSIS 가능성이 있으나 파생·기준연도·시계열·모집단 정렬 필요
OTHER_OFFICIAL      공식 자료지만 KOSIS 외부 기관 근거 가능성이 높음
PRIVATE_SOURCE      민간 기관·기업·시장 데이터 필요
PLATFORM_SOURCE     플랫폼 수치 필요: 유튜브, SNS, 앱, 영화/음원 차트 등
FORECAST_OR_OPINION 전망·예측·의견·해석이라 현재 공식 통계 검증 부적합
NOISE               날짜, 순번, 나이, 경기기록 등 사실검증 대상이 아닌 숫자
UNKNOWN             자동 분류 불확실 — 사람 검토 필요
```

### 2.2 Economic Domain

```text
employment_labor
prices_inflation
population_household
agriculture_fishery
industry_production
trade_customs
real_estate
finance_market
national_accounts_macro
household_income_consumption
business_company
energy_environment
small_business_local
unknown
```

### 2.3 Routing Output JSON

```json
{
  "article_id": "...",
  "section": "경제",
  "sentence": "지난해 실업률은 7.2%였다.",
  "is_numeric_claim": true,
  "claim_type": "scale",
  "economic_domain": "employment_labor",
  "source_type": "KOSIS_DOMESTIC",
  "kosis_mapping_likelihood": "HIGH",
  "expected_source": "KOSIS 고용·노동 통계",
  "expected_kosis_query_terms": ["실업률", "고용률"],
  "needs_calculation": false,
  "risk_type": ["시점 정렬", "% vs %p"],
  "route": "KOSIS_RETRIEVAL",
  "confidence": 0.86,
  "reason": "실업률은 KOSIS 국내 고용통계에서 직접 조회 가능한 대표 지표"
}
```

---

## 3. Domain-to-Source Routing Rules

| 경제 기사 수치 영역 | 예시 Claim | 1차 라우팅 | 이유 |
|---|---|---|---|
| 고용·노동 | 실업률, 고용률, 취업자 수 | KOSIS_DOMESTIC | KOSIS 대표 커버리지 |
| 물가 | 소비자물가, 생활물가, 품목별 지수 | KOSIS_BUT_COMPLEX | KOSIS 가능, 기준연도/지수 주의 |
| 인구·가구 | 1인 가구, 출생아, 고령화 | KOSIS_DOMESTIC | 인구동향·총조사 |
| 농업 | 농가 수, 재배면적, 고령 농가 | KOSIS_BUT_COMPLEX | KOSIS 가능, 파생 계산 많음 |
| 산업생산 | 제조업 생산, 광공업 생산 | KOSIS_DOMESTIC 또는 OTHER_OFFICIAL | KOSIS 가능하지만 원출처 확인 필요 |
| 수출입 | 수출액, 무역수지 | OTHER_OFFICIAL | 관세청/무역협회 우선 가능성 |
| 부동산 | 아파트값, 전셋값, 거래량 | OTHER_OFFICIAL | 한국부동산원/국토부 가능성 높음 |
| 금융시장 | 주가, 환율, 금리, 코스피 | PRIVATE_SOURCE 또는 OTHER_OFFICIAL | 거래소/한은/시장 데이터 |
| 거시경제 | GDP, 성장률 | OTHER_OFFICIAL | 한국은행 ECOS 가능성 높음 |
| 기업실적 | 매출, 영업이익, 투자액 | PRIVATE_SOURCE | 기업 공시/IR |
| 소상공인 | 매출, 폐업률 | OTHER_OFFICIAL 또는 PRIVATE_SOURCE | 중기부/국세/카드사 혼재 |
| 전망 | 내년 성장률, 예상 물가 | FORECAST_OR_OPINION | 현재 사실검증 회피 |

---

## 4. Step-by-Step Implementation Plan

### Task 1: Create source classification fixtures

**Objective:** 경제면 수치 Claim 라우팅 기준을 테스트 가능한 작은 데이터로 고정한다.

**Files:**
- Create: `data/goldenset/source_routing_seed.jsonl`
- Create: `tests/test_source_classifier.py`

**Seed examples:**

```jsonl
{"sentence":"지난해 실업률은 7.2%로 전년보다 0.3%p 상승했다.","section":"경제","expected_source_type":"KOSIS_DOMESTIC","expected_domain":"employment_labor"}
{"sentence":"소비자물가지수는 전년보다 3.1% 올랐다.","section":"경제","expected_source_type":"KOSIS_BUT_COMPLEX","expected_domain":"prices_inflation"}
{"sentence":"서울 아파트값은 이번 주 0.3% 상승했다.","section":"경제","expected_source_type":"OTHER_OFFICIAL","expected_domain":"real_estate"}
{"sentence":"코스피는 장중 3000선을 돌파했다.","section":"경제","expected_source_type":"PRIVATE_SOURCE","expected_domain":"finance_market"}
{"sentence":"내년 경제성장률은 2.4%에 이를 전망이다.","section":"경제","expected_source_type":"FORECAST_OR_OPINION","expected_domain":"national_accounts_macro"}
```

**Validation:**
- `python -m pytest tests/test_source_classifier.py -v`

---

### Task 2: Add source classification dataclass

**Objective:** Claim과 Evidence 사이에 들어갈 라우팅 객체를 정의한다.

**Files:**
- Modify: `clafact/schemas.py`

**Fields:**

```python
@dataclass
class SourceRoute:
    source_type: str
    economic_domain: str
    kosis_mapping_likelihood: str
    expected_source: str = ""
    expected_kosis_query_terms: list[str] = field(default_factory=list)
    needs_calculation: bool = False
    risk_type: list[str] = field(default_factory=list)
    route: str = ""
    confidence: float = 0.0
    reason: str = ""
```

**Validation:**
- Existing tests must still pass.

---

### Task 3: Implement rule-based economic source classifier

**Objective:** KOSIS와 비-KOSIS 경제 Claim을 1차로 자동 분류한다.

**Files:**
- Create: `clafact/pipeline/source_classify.py`
- Test: `tests/test_source_classifier.py`

**Rule groups:**

```python
KOSIS_KEYWORDS = {
    "employment_labor": ["실업률", "고용률", "취업자", "청년 고용", "경제활동인구"],
    "prices_inflation": ["소비자물가", "생활물가", "물가지수", "물가상승률"],
    "population_household": ["출생아", "사망자", "1인 가구", "고령", "인구"],
    "agriculture_fishery": ["농가", "과수", "재배면적", "어가", "농림어업"]
}

OTHER_OFFICIAL_KEYWORDS = {
    "trade_customs": ["수출", "수입", "무역수지", "관세청"],
    "real_estate": ["아파트값", "전셋값", "매매가", "한국부동산원", "국토부"],
    "national_accounts_macro": ["GDP", "국내총생산", "경제성장률", "한국은행"]
}

PRIVATE_KEYWORDS = {
    "finance_market": ["코스피", "코스닥", "주가", "시총", "환율", "비트코인"],
    "business_company": ["영업이익", "매출", "투자액", "분기 실적"]
}
```

**Key rule:**
- KOSIS keyword hit + 통합검색 후보 있음 → `KOSIS_DOMESTIC` or `KOSIS_BUT_COMPLEX`
- KOSIS keyword hit but complex indicator/index/derived ratio → `KOSIS_BUT_COMPLEX`
- Other official keyword hit → `OTHER_OFFICIAL`
- Forecast markers → `FORECAST_OR_OPINION`
- Stock/crypto/company terms → `PRIVATE_SOURCE`

---

### Task 4: Integrate KOSIS integrated-search evidence as confirmation signal

**Objective:** 규칙 분류만으로 확정하지 않고, KOSIS 통합검색 결과로 `KOSIS` 가능성을 보강한다.

**Files:**
- Create or modify: `clafact/pipeline/retrieve_kosis.py`
- Modify: `clafact/pipeline/source_classify.py`

**Logic:**

```text
1. Claim에서 검색어 후보 1~3개 생성
2. KOSIS 통합검색 Top 10 수집
3. tblId, tblNm, statNm, period range 확인
4. 관련 결과가 있으면 KOSIS likelihood 상향
5. 결과가 없거나 검색어가 너무 넓으면 UNKNOWN 또는 OTHER_OFFICIAL 유지
```

**Important:**
- 로컬 개발망에서는 KOSIS 비브라우저 호출이 차단될 수 있으므로 Fixture부터 구현한다.
- 실 호출 검증은 클라우드/브라우저 경로에서 별도 실행한다.

---

### Task 5: Add EDA script for real Chosun dataset

**Objective:** 데이터셋 도착 후 섹션별 수치 Claim과 source_type 분포를 자동 산출한다.

**Files:**
- Create: `scripts/classify_news_sources.py`

**Input:**
- JSONL/CSV 기사 데이터셋

**Output:**
- `reports/source_classification_summary.json`
- `reports/source_classification_by_section.csv`
- `reports/source_classification_candidates.jsonl`

**Metrics:**

```text
section별 기사 수
section별 숫자 문장 수
section별 numeric claim 후보 수
source_type 분포
KOSIS_DOMESTIC 후보 Top domains
OTHER_OFFICIAL 후보 Top domains
UNKNOWN / 사람 검토 필요 문장
```

---

### Task 6: Add human review workflow

**Objective:** 자동 분류를 바로 공식 라벨로 쓰지 않고, 사람이 검토할 수 있게 만든다.

**Files:**
- Modify: `scripts/review_cli.py` or create `scripts/review_source_routes.py`

**Review labels:**

```text
accept
change_source_type
change_domain
mark_unknown
promote_to_golden_candidate
```

**Asset connection:**
- KOSIS로 잘못 보낸 Claim → source routing rule 수정
- OTHER_OFFICIAL인데 KOSIS였던 Claim → alias/query rule 추가
- UNKNOWN 반복 → 새 domain/source pattern 추가

---

### Task 7: Add evaluation metrics

**Objective:** source routing 자체를 평가 가능한 모듈로 만든다.

**Files:**
- Modify: `clafact/eval/metrics.py`
- Modify: `clafact/eval/harness.py`

**Metrics:**

```text
source_type_accuracy
KOSIS_precision
KOSIS_recall
OTHER_OFFICIAL_precision
UNKNOWN_rate
section_domain_distribution
```

**Main success criterion:**
- KOSIS로 보내는 Claim의 Precision을 높게 유지한다.
- 애매한 것은 UNKNOWN/판단불가로 보내도 된다.
- KOSIS가 아닌 Claim을 억지로 KOSIS에 매핑하지 않는 것이 핵심이다.

---

## 5. Automation Strategy

### 5.1 Pipeline Position

```text
Article
→ Sentence Split
→ Numeric Claim Detection
→ Claim Parsing
→ Source Classification  ← 신규
→ KOSIS Retrieval or Non-KOSIS Queue
→ Verdict or Out-of-Scope/Needs External Source
```

### 5.2 Routing Decision

```text
KOSIS_DOMESTIC / KOSIS_BUT_COMPLEX
→ KOSIS 경로 A/B/C/D 검색

OTHER_OFFICIAL
→ 외부 공식자료 큐로 보냄. 1차 PoC에서는 Verdict 보류 가능.

PRIVATE_SOURCE / PLATFORM_SOURCE
→ 1차 PoC 범위 밖. 필요시 별도 근거원 확장 후보.

FORECAST_OR_OPINION / NOISE
→ Verdict 회피 또는 Claim 제외.

UNKNOWN
→ 사람 검토 큐.
```

---

## 6. Risks / Tradeoffs

1. **KOSIS Recall vs Precision**
   - KOSIS 가능 Claim을 놓치면 Coverage가 낮아짐.
   - KOSIS가 아닌 Claim을 KOSIS로 보내면 오판정 위험이 커짐.
   - 1차 PoC에서는 Precision 우선이 안전하다.

2. **경제면의 혼합 출처 문제**
   - 한 기사 안에서도 실업률은 KOSIS, 기준금리는 ECOS, 주가는 거래소일 수 있다.
   - 기사 단위가 아니라 Claim 문장 단위로 라우팅해야 한다.

3. **기관명 힌트의 편향**
   - 기사에 “통계청”이 없다고 KOSIS가 아닌 것은 아니다.
   - 반대로 “정부 통계”라고 해도 KOSIS가 아닐 수 있다.
   - 키워드 + 통합검색 + 사람 검토가 필요하다.

4. **연예/스포츠 같은 낮은 KOSIS 영역**
   - 수치가 많아도 KOSIS 근거가 아닐 가능성이 크다.
   - 자동 분류에서 빠르게 DROP/P3로 보내야 비용을 줄인다.

---

## 7. Open Questions for Human Team

1. 1차 PoC에서 `OTHER_OFFICIAL`을 단순 판단불가로 둘 것인가, 아니면 “근거원 확장 후보”로 별도 큐를 만들 것인가?
2. 경제면에서 한국은행 ECOS를 2차 Evidence source로 열 것인가?
3. 부동산 수치는 KOSIS 외부 공식자료가 많으므로 1차 PoC에서 제외할 것인가, P2로 둘 것인가?
4. source classification의 목표는 KOSIS 후보 최대 회수율인가, KOSIS 오매핑 최소화인가? 권장: 오매핑 최소화.

---

## 8. Verification

Run after implementation:

```bash
python -m pytest tests/test_source_classifier.py -v
python -m pytest tests/test_detect.py tests/test_parse.py tests/test_retrieve.py tests/test_run.py -v
python scripts/run_eval.py
python scripts/classify_news_sources.py --input data/raw/chosun_2025.jsonl --out reports/
```

Expected outputs:

```text
source_type_accuracy reported
KOSIS_precision reported
section별 source_type 분포 generated
UNKNOWN review queue generated
```

---

## 9. First Practical Milestone

**G-SOURCE-1:** 샘플/파일럿 Claim 50건 기준으로 다음을 만든다.

- 경제면 Claim source_type 분류 결과
- KOSIS 후보와 비-KOSIS 후보 분포
- UNKNOWN 사람 검토 큐
- KOSIS로 보낸 Claim의 오매핑 사례 목록
- source routing rule v0.1

이 게이트를 통과하면 2025년 조선일보 전체 데이터셋이 도착했을 때 바로 대량 EDA를 실행할 수 있다.
