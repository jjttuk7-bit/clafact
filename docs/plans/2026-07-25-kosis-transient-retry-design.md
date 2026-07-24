# KOSIS 일시적 연결 실패 재시도 설계

## 목표

KOSIS Open API의 시간 초과·연결 실패를 수치 검증 실패로 오인하지 않게 한다. 원문 오류는 내부에 보존하고, 화면에는 간결한 재시도 안내를 표시한다. 재시도 가능한 Claim은 다음 검증 실행에서 예약 시각 이후 자동으로 다시 처리한다.

## 범위

- `URLError`·`TimeoutError`에서 비롯된 KOSIS 연결 실패만 일시적 실패로 분류한다.
- HTTP 오류, API 응답 오류, 수치·근거 불일치는 기존 정책을 유지한다.
- Streamlit은 상주 작업자가 아니므로 정해진 시각에 자체 실행하지 않는다. 사용자의 다음 일괄/개별 검증 또는 외부 배치 실행이 예약된 Claim을 처리한다.

## 저장 모델

`claims`에 다음 필드를 안전한 SQLite 마이그레이션으로 추가한다.

- `retry_count INTEGER NOT NULL DEFAULT 0`
- `next_retry_at TEXT NOT NULL DEFAULT ''`
- `failure_kind TEXT NOT NULL DEFAULT ''`

연결 실패 시 `failure_kind='KOSIS_CONNECTION'`을 기록하고, 재시도 횟수에 따라 다음 실행 가능 시각을 저장한다. 최대 3회 자동 재시도 이후에는 기존 FAILED 상태로 남긴다.

## 처리 흐름

1. KOSIS 호출이 연결 시간 초과로 실패한다.
2. 배치가 실패를 `KOSIS_CONNECTION`으로 분류한다.
3. 아직 자동 재시도 한도 안이면 Claim을 `PENDING`으로 되돌리고 다음 재시도 시각을 저장한다.
4. `fetch_pending`은 `next_retry_at`이 비었거나 현재 시각 이전인 Claim만 반환한다.
5. 후속 검증 실행이 예약 시각이 지난 Claim을 자동 처리한다.
6. 성공한 판정·사람의 수동 재시도는 재시도 메타데이터를 초기화한다.

## 화면 정책

- 사용자에게는 긴 Python traceback을 표시하지 않는다.
- `KOSIS 연결이 지연되고 있습니다. 다음 재시도 가능 시각 이후 다시 검증합니다.`를 표시한다.
- 예정 시각과 재시도 횟수를 함께 보여 준다.
- 수동 `KOSIS 재검증 실행`은 유지하되, 예약 시각 전에는 안내만 표시한다.

## 검증

- 연결 실패가 PENDING·예약 시각·재시도 횟수로 저장되는지 테스트한다.
- 예약 전 Claim이 처리 대상에서 제외되는지 테스트한다.
- 예약 이후 Claim이 처리되는지 테스트한다.
- 화면에 traceback 대신 사용자 안내가 표시되는지 소스 계약 테스트로 확인한다.
