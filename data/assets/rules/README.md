# A2 규칙 카드 색인

규칙 카드는 **문서가 아니라 실행 자산**이다. 탐지형 카드의 `pattern`은 런타임에 로드되어
동작을 바꾸고(`pipeline/detect.py`), 판정형 카드는 `pipeline/run.py`·`verdict.py`에 구현된다.
**테스트 없는 규칙은 등록이 거부된다** (`assets/rules.py`).

각 카드의 `origin_case` 필드에 **이 규칙이 어떤 실패에서 태어났는지**가 적혀 있다.
"왜 이런 규칙이 있지?"를 물을 필요가 없게 하는 것이 이 필드의 목적이다.

## 전체 목록 (15종)

| ID | 이름 | 유형 | 태어난 계기 | 테스트 |
|---|---|---|---|---|
| A2-0001 | 임계 표현 부등호 판정 | verdict | "넘어섰다"를 단순 일치로 보던 오판 | test_verdict |
| A2-0002 | 반올림은 기사 단위 스케일 기준 | verdict | 자릿수 기준 불일치 | test_verdict |
| A2-0003 | 숫자 없는 최상급 탐지 | detection | "사상 최악"을 규칙 필터가 놓침 | test_detect |
| A2-0004 | 신뢰도 그라데이션 | verdict | 확신 정도를 표현할 수단 부재 | test_verdict |
| A2-0005 | 상대 시점 정규화 | period | "올해"·"지난해"를 절대 시점으로 | test_parse |
| A2-0006 | 복합명사 가드 | detection | 단위어가 주제어를 뭉개는 문제 | test_query_gen |
| A2-0007 | 연령 구간 합산 ÷ 전체 파생계산 | verdict | 과수 농가 65세 이상 비율 | test_verdict |
| A2-0008 | KOSIS 결합 차원 접두 형식 | retrieval | 실 API의 "영농형태 : 과수" 형식 | test_retrieve |
| A2-0009 | 전년 대비 증감률 재현 | verdict | 표에 없는 증감률을 계산으로 | test_verdict |
| A2-0010 | 빈 사전 falsy 버그 | code | `aliases or AliasDict()`가 빈 사전 무시 | test_retrieve |
| ~~A2-0011~~ | *(예약: 이중계상 UP_ITM_ID)* | — | 실 API 메타 필요로 미구현 — **번호 갭** | — |
| A2-0012 | 잠정치 회피 | period | KOSIS는 과거 공표값(vintage) 미제공 | test_provisional |
| A2-0013 | 지수 기준연도 회피 | period | 지수는 기준연도 따라 값이 달라짐 | test_baseyear |
| **A2-0014** | **해외 주체 가드** | source | 일본·미국 물가를 한국 통계와 대조한 오판 3건 | test_source_classifier |
| **A2-0015** | **시점 입도 정합** | period | 월간 주장을 연간 통계와 대조한 오판 3건 | test_granularity |
| **A2-0016** | **비교 기준 정합** | verdict | 전월비를 전년동월비로 오인한 오판 | test_basis |

굵게 표시한 세 종은 **첫 실 판정(2026-07-20)의 오판에서 태어났다** — 픽스처로는 발견할 수 없었던 결함들이다.

## 다음 채번

**A2-0017.** (A2-0011은 이중계상용으로 예약되어 있어 번호에 갭이 있다 — 버그가 아니다.)

## 후보 (아직 카드 아님)

- **모집단 정렬**: "175개 품목 평균"(부분집합)을 전체 CPI와 대조하는 문제
- **지수 기준연도 표기 오파싱**: "115.71(2020년=100)"의 기준연도를 주장 시점으로 읽음

## 카드 추가하는 법

```python
from clafact.assets.rules import RuleRegistry
RuleRegistry("data/assets/rules").create(
    type="detection",           # detection이면 pattern 필수 (런타임 로드됨)
    name="...", condition="...", handling="...",
    origin_case="어떤 실패에서 나왔는가",   # ← 이 필드를 비우지 말 것
    origin_run="F2026...",  test="tests/test_xxx.py")
```

또는 데모의 🔥플라이휠 탭에서 UI로 생성할 수 있다.
