# KOSIS 실패 진단·재시도 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |

실패 저장 문자열 앞에 예외 타입과 안전한 메시지를 두고, 실패 Claim을 PENDING으로 되돌린 뒤 기존 검증 경로를 재실행하는 버튼을 제공한다. 키는 오류에 포함되지 않는다.
