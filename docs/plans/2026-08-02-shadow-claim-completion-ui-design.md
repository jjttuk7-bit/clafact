# Shadow Claim 완료 UI 설계

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Approved |
| Version | v0.1 |
| Last Updated | 2026-08-02 |

## 무엇을 하는가

쉐도우 모드에서 사용자가 문장과 확정 근거를 선택한 뒤 `Claim 완료`를 명시적으로 누르면, KOSIS 스냅샷 기반 판정을 불변 기록으로 저장하고 화면과 CSV에서 같은 결과를 확인하게 한다.

## 핵심 구조

기존 `shadow_run_id`, `row_index`, 선택된 근거와 값 비교 결과를 입력으로 사용한다. 완료 기록에는 문장, 기사 수치, 판정(`match`/`mismatch`/`hold`), 차이값, KOSIS 스냅샷 전체, 재현 URL을 보관한다. 동일 문장·근거·스냅샷 조합은 중복 저장하지 않는다.

## 화면 흐름

1. 사용자는 쉐도우 실행의 문장을 선택한다.
2. 연결된 KOSIS 근거 중 하나를 선택한다.
3. `Claim 완료`를 누른다.
4. 결과 카드가 일치·불일치·보류와 핵심 근거를 표시한다.
5. 완료 Claim CSV 내려받기는 화면의 결과와 동일한 필드를 담는다.

## 제외 범위

자동 확정, 기존 근거·값 비교 체계의 전면 재설계, 단위 변환·복합 계산 Claim은 이번 작업에서 제외한다.

## 검증 기준

실제 쉐도우 실행의 문장 1건과 KOSIS 근거 1건으로 완료 기록을 만들고, 화면 결과와 CSV의 판정·스냅샷 ID·근거 URL이 일치함을 자동 테스트와 수동 확인으로 검증한다.
