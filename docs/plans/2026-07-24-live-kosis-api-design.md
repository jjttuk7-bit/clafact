# 실 KOSIS API 검증 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |

## Goal

Streamlit 운영 화면의 검증 실행이 로컬 fixture가 아니라 KOSIS Open API의 통합검색과 통계자료 조회를 사용하게 한다.

## Design

`load_engine()`은 `HttpKosisClient`와 `KosisSearchIndex`를 반환한다. KosisSearchIndex는 추출된 지표어로 KOSIS 통합검색을 수행하고, HttpKosisClient는 선택된 표의 실제 행을 조회한다. KOSIS_API_KEY는 Streamlit Secrets의 루트 값이 제공하는 환경변수만 읽는다.

기존 HttpKosisClient의 호출 예산·분당 제한·재시도·키 마스킹을 유지한다. API 오류는 기존 버튼별 예외 처리로 화면에 표시하며, 키와 요청 URL의 실제 API 키는 화면이나 감사 로그에 노출하지 않는다. HCX 연결과 fixture 기반 오프라인 테스트는 변경하지 않는다.

## Validation

소스 회귀 테스트로 실 클라이언트와 실 검색 인덱스가 배선되는지 검증한다. 네트워크 없는 기존 테스트와 컴파일을 실행한다.
