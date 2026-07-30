# Shadow Lab 설계

| 항목 | 내용 |
| --- | --- |
| Author | Human Team + Codex |
| Reviewed by | Human Team |
| Managed by | Codex |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-28 |

## 목적

기존 ClaFact 운영 판정에 영향을 주지 않고, 동일 뉴스 입력에 대해 기존 방식과 새 분석 방법을 병렬 실행·비교·저장·검토하는 연구용 Shadow Lab을 검증 실험실 안에 제공한다.

## 결정

- 새 앱이나 별도 운영 DB를 만들지 않는다.
- 기존 `검증 실험실`과 연구용 `ExperimentStore`를 확장한다.
- Shadow 실행 결과는 연구 저장소에만 기록한다. 운영 `Store`, 운영 리뷰 큐, 발행 결과를 변경하지 않는다.
- 사람은 전체 결과가 아니라 방법 간 충돌·필수 필드 누락·저신뢰 사례만 검토한다.
- 사람이 승인한 사례는 즉시 운영 규칙으로 반영하지 않고, 연구용 골든셋·별칭·규칙 후보로만 승격한다.

## 사용자 흐름

```text
검증 실험실 진입
→ 정책 선택(도메인·데이터원·보류 기준)
→ 기사/문장/CSV 입력 선택
→ Shadow 실험 실행
→ 기존 방식과 실험 방식의 결과 비교
→ 충돌·저신뢰 사례만 검토
→ 실행 결과 자동 저장
→ CSV·JSONL·Markdown 다운로드
→ 승인 사례만 골든셋 후보로 승격
```

## 구성 요소

| 구성 | 책임 | 저장 위치 |
| --- | --- | --- |
| Shadow Policy | 실험 범위, 판정·보류·검토 조건 정의 | 연구 실행 설정 |
| Shadow Runner | 기존 파이프라인과 실험 방법을 동일 입력으로 실행 | 연구 실행 결과 |
| Comparison Builder | 방법별 결과를 비교하고 충돌·위험도를 계산 | 연구 실행 결과 |
| Review Queue | 충돌·저신뢰 사례만 사람에게 노출 | 연구 검토 기록 |
| Export | 원본 입력, 설정, 결과, 오류, 지표를 내보냄 | 다운로드 파일 |
| Promotion Gate | 사람 승인 사례를 골든셋 후보로 승격 | 연구 골든셋 |

## 정책 모델

Shadow 실행은 최소한 아래 정책을 보관한다.

```text
domain: population
evidence_source: KOSIS
claim_types: absolute_value, change, growth_rate, ratio, ranking
default_when_uncertain: insufficient_evidence
review_when: required_slot_missing, candidate_conflict,
             definition_mismatch, unit_or_time_ambiguous
```

정책과 실행 방법·데이터 스냅샷·정답셋 버전은 모든 실행 결과에 함께 저장한다.

## 화면 설계

`검증 실험실` 안에 Shadow Lab 섹션을 추가한다.

1. 입력·정책 카드: 입력 범위와 비교할 방법을 선택한다.
2. 실행 카드: Shadow 실행 버튼과 ‘운영 결과는 변경되지 않음’ 안내를 보여준다.
3. 요약 카드: 처리 수, 일치 수, 충돌 수, 검토 필요 수, 보류 수, 지연 시간을 보여준다.
4. 비교 표: 입력별 기존 방식·실험 방법·후보 표·상태를 보여준다.
5. 검토 큐: 충돌 이유와 승인·수정·보류 선택을 제공한다.
6. 내보내기: CSV, JSONL, Markdown 결과를 다운로드한다.

## 안전성

- 운영 DB와 연구 DB를 혼용하지 않는다.
- Shadow 실행은 운영 claim의 상태, tier, evidence, review를 쓰지 않는다.
- KOSIS 호출 실패 또는 분석 실패는 운영 오류로 전파하지 않고 연구 실행 오류로 기록한다.
- 출력에 표 ID·원본 URL·조회 시점·선택 조건이 없으면 ‘근거 완결’로 표시하지 않는다.

## 변경 기록 원칙

각 구현 변경은 `docs/SHADOW_LAB_CHANGELOG.md`에 변경 ID, 목적, 수정 파일, 영향 범위, 테스트, 결과, 롤백 방법을 기록한다. 운영 코드 영향이 있는 변경은 별도 승인 게이트를 둔다.

## 승인 기준

- Shadow 실행이 운영 결과를 변경하지 않는다.
- 실행 결과에 정책·방법·데이터 버전이 저장된다.
- 충돌과 저신뢰 사례만 검토 큐에 표시된다.
- 실행 결과를 CSV·JSONL·Markdown으로 내보낼 수 있다.
- 기존 검증 실험실 회귀 테스트가 통과한다.
