# KOSIS 재검증 피드백 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |


실패 Claim의 재검증 버튼은 배치 결과를 표시하지 않은 채 즉시 `st.rerun()`을 호출한다. 배치가 오류를 Claim 단위로 저장하므로 사용자는 재실행 여부를 알 수 없다.

재검증 시작 시 `st.spinner`로 진행 상태를 표시한다. 완료 후 처리·실패 건수를 `st.session_state`에 저장하고 새로고침 뒤 화면 상단에 한 번 표시한다. 실패 카드에서는 저장된 최신 오류와 처리 시각을 계속 표시한다. 현재 실행 코드 버전도 검증 화면에 표시해 배포 반영 여부를 확인할 수 있게 한다.

검증 엔진·판정 로직·데이터베이스 스키마는 변경하지 않는다. 세션 메시지는 일회성으로 소비하며, 다음 화면 실행에서 제거한다.
