# KOSIS objL 누락 자동 보완 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |


## 배경

실 KOSIS 통계자료 API가 `err: 20` 및 `필수요청변수값이 누락되었습니다. (objL)`로 응답했다. 현재 요청은 `objL1=ALL`만 보내고 `objL2`~`objL8`은 빈 문자열로 보낸다. 일부 통계표는 추가 분류 수준을 요구한다.

## 결정

`HttpKosisClient.fetch_data()`에서만 오류 코드 20을 처리한다. 최초 요청이 오류 20이면, 아직 호출자가 지정하지 않은 분류 수준을 `objL2=ALL`부터 하나씩 추가해 다시 호출한다. 첫 리스트 응답을 받으면 즉시 중단하며, 오류 20이 아닌 오류·연결 실패·HTTP 오류는 재시도하지 않고 기존 동작대로 전파한다.

각 호출은 기존 `_call()`을 사용하므로 API 호출 예산과 분당 제한을 그대로 적용한다. 모든 수준을 시도해도 오류 20이면 마지막 오류를 전파한다. 이 동작은 표별 분류 요구를 만족하기 위한 조회 보완이며, 통계 판정 로직이나 Fixture 클라이언트에는 영향을 주지 않는다.

## 검증

HTTP 호출을 모의해 첫 응답이 오류 20, 두 번째 응답이 행 목록인 경우를 재현한다. 두 번째 URL에 `objL2=ALL`이 포함되고, 요청 예산이 두 번 차감되며, 행이 반환되는지를 확인한다. 이어 일반 KOSIS 오류는 추가 호출 없이 전파되는지도 확인한다.
