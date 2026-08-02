# Shadow 저장 실행 불러오기 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Approved |
| Version | v0.1 |
| Last Updated | 2026-08-02 |

## 무엇을 하는가

최근 저장된 Shadow 실행 20개 중 하나를 선택해 현재 화면의 실행 대상으로 전환한다.

## 핵심 내용

선택 상자는 실행 시각·짧은 실행 ID·문장 수를 표시한다. 선택은 `shadow_lab_run_id` 세션 값만 바꾸며, 저장된 실행·근거·비교·완료 Claim은 수정하지 않는다. 기존 Claim 완료와 CSV 흐름을 그대로 재사용한다.

## 다음 연결

실측 KOSIS 사례를 화면에서 불러와 `Claim 완료`와 CSV의 판정·스냅샷 ID·재현 URL 일치를 실제로 확인한다.
