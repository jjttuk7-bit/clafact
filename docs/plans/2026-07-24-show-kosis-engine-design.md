# KOSIS 검증 엔진 표시 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |

결과 카드에서 저장된 audit의 engine과 processed_at을 읽는다. HttpKosisClient는 실 KOSIS Open API, FixtureKosisClient는 데모 fixture, 없는 값은 이전 결과로 정직하게 표시한다. DB 변경은 없다.
