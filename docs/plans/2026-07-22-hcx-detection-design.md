# HCX 탐지 보조 설계

**Author:** Codex
**Reviewed by:** Human Team
**Managed by:** Human Team
**Status:** Approved
**Version:** v0.1
**Last Updated:** 2026-07-22

## 목표

규칙 기반 수치 Claim 탐지에 HCX 2차 판별 신호를 선택적으로 추가한다.

## 안전 계약

- 기본 모드는 규칙만 사용한다.
- `CLAFACT_HCX_MODE=live`에서만 HCX를 호출한다.
- HCX 결과는 탐지 후보를 제거하지 않는 보조 신호다.
- 키 누락, 오류, JSON 파싱 실패는 규칙 결과로 폴백한다.
- 허용 응답은 `{"verifiable": true|false}`다.

## 검증

모드 선택·정상 JSON·오류 폴백을 오프라인 테스트로 고정한 뒤 실제 호출 1회만 스모크한다.
