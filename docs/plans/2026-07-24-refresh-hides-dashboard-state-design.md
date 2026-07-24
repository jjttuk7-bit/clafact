# Refresh Hides Dashboard State Design

| 항목 | 내용 |
|---|---|
| Author | ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |

## Goal

브라우저 새로고침 후 이전 업로드와 누적 운영 통계가 화면에 노출되지 않게 한다. SQLite 운영 데이터는 삭제하지 않는다.

## Design

서버 세션에 `dashboard_initialized` 상태를 두고, 페이지 진입 직후에는 운영 홈의 누적 통계 카드를 숨긴다. CSV 기사 등록이 성공하면 이 상태를 활성화하여 해당 업로드의 결과와 통계를 표시한다. `새 업로드 시작`은 현재 업로드 상태를 비우고 통계 카드는 숨긴다.

## Data Safety

`Store`의 기사·Claim·검증 결과 테이블에는 쓰기 또는 삭제를 추가하지 않는다. 이 변경은 Streamlit 화면 표시와 세션 상태만 변경한다.

## Validation

소스 수준 회귀 테스트로 초기 상태에서 카드 표시가 조건부인지, 등록 성공 시 표시 상태를 활성화하는지, 새 업로드 시작 시 비활성화하는지를 검증한다.
