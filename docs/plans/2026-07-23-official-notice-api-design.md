# Official Notice Evidence API Design

| 항목 | 내용 |
|---|---|
| Author | ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-23 |

## Goal

공식 조사·시행 일정 Claim에 대해 KOSIS 수치표 대신 등록된 공식 공지 근거를 사용해 판정한다.

## API

- `POST /internal/claims/{claim_id}/official-notice`
  - Body: `organization`, `url`, `effective_date`
  - URL은 `http` 또는 `https`만 허용한다.
- `GET /internal/claims/{claim_id}/official-notice`
  - 등록 근거와 현재 판정 결과를 반환한다.

## Data and Verdict Flow

SQLite에 Claim별 공식 근거를 저장한다. 등록 대상은 `OFFICIAL_ANNOUNCEMENT` Claim만 허용한다.

- 문장에서 날짜를 추출할 수 있고 `effective_date`와 다르면 `mismatch`
- 날짜가 일치하거나 문장에서 날짜를 추출할 수 없으면 `match`
- 아직 근거가 없으면 Claim은 `CLASSIFIED` 상태를 유지하고 화면에는 `공식 근거 확인 필요`로 표시한다.

등록 시 `evidence_json`에 공식 기관·URL·시행일을 기록하고, Claim 결과를 즉시 갱신한다. KOSIS 조회 큐에는 넣지 않는다.

## Testing

저장소 단위 테스트로 근거 등록, 비공식 공지 Claim 거부, 날짜 일치·불일치 판정을 검증한다. API 테스트로 유효 URL, 잘못된 URL, 조회 응답을 검증한다.