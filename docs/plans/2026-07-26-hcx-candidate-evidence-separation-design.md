# HCX 후보 탐지·근거 충분성 분리 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-26 |

## 문제

HCX 단독 판별은 현재 “공식 통계로 즉시 검증 가능한 수치 주장인가”를 하나의 불리언으로 반환한다. 이 때문에 수치·비교·시점이 있어 검증 후보인 문장이 기사 안의 직접 공식 인용이 부족하다는 이유로 후보 단계에서 제외된다.

## 결정

HCX 판별 결과를 다음 두 축으로 분리한다.

1. `candidate`: 기사 문장이 후속 검증 대상이 될 수 있는 수치·비교·시점 주장인가.
2. `evidence_status`: 기사 원문 안에 즉시 검증 가능한 공식 근거가 충분한가. 값은 `sufficient`, `needs_retrieval`, `not_applicable`, `unknown`이다.

`candidate=false`는 숫자 식별자·전화번호·순수 의견처럼 후보가 아닌 경우에만 사용한다. `candidate=true` 및 `evidence_status=needs_retrieval`은 정상적인 탐지 결과다.

## 인터페이스

HCX는 JSON만 반환한다.

```json
{
  "candidate": true,
  "candidate_reason": "2.6%와 15개월 비교가 있는 수치 주장",
  "evidence_status": "needs_retrieval",
  "evidence_reason": "기사 내부에는 통계표 또는 직접 인용이 충분하지 않음",
  "quoted_spans": ["지난해 7월(2.6%) 이후 15개월만에 가장 높은 수치"]
}
```

파싱 실패·API 오류는 후보를 `unknown`으로 만들고, 사유에 오류를 남긴다. 원문에 없는 인용 구간은 표시하지 않는다.

## 화면

- HCX 후보 문장 수: `candidate=true`만 집계한다.
- 문장 상세: `HCX 후보 판정`, `근거 상태`, `각 사유`, `원문 인용 구간`을 별도 줄로 표시한다.
- 비교표: 후보 탐지 결과는 기존 열에, 근거 상태는 새 열에 표시한다.
- 하이브리드: Python 1차 후보 → HCX 후보 판정/근거 상태를 함께 표시한다. 근거 부족은 후보를 제거하지 않는다.

## 품질 기준

문장 “이같은 물가 상승률은 지난해 7월(2.6%) 이후 15개월만에 가장 높은 수치다.”는 HCX 계약 결과에서 `candidate=true`, `evidence_status=needs_retrieval`이어야 한다. API 호출이 실패하면 거짓 미탐지 대신 실패 상태를 표시한다.
