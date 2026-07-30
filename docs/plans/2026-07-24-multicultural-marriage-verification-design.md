# 다문화 혼인 비율 검증 설계

| 항목 | 내용 |
|---|---|
| Author | ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Superseded |
| Version | v0.2 |
| Last Updated | 2026-07-30 |

> **Status note:** This design was implemented and superseded by commit `f26407f` (`feat: verify registered multicultural share metrics`). The implementation uses the official share-metrics registry and also covers multicultural-birth share claims.

## 문제

다문화 혼인 비율 주장은 수치와 시점이 추출됐지만, 샘플 메타에 대응 통계표가 없어 무관한 표를 선택하고 판단불가로 끝난다. 비율은 분자와 분모를 계산해야 하므로 단일 수치 대조만으로는 검증할 수 없다.

## 설계

`다문화 혼인`을 통계표 메타와 별칭에 추가한다. 2024년 다문화 혼인 건수와 전체 혼인 건수를 같은 시점에 조회하고, 비율과 전년 대비 퍼센트포인트 변화를 계산한다. 조회 실패도 선택된 표·시점·사유를 감사 로그로 남긴다.

## 완료 기준

- 2024년 다문화 혼인 비중 9.6%, 전년 대비 1.0%p 감소 주장이 `match`가 된다.
- 결과에는 계산 근거와 감사 로그가 남는다.
- 기존 단일 수치 검증 회귀 테스트가 유지된다.
