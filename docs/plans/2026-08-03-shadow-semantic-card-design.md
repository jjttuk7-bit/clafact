# Shadow Mode 성장형 Semantic Card 설계

## 목적

KOSIS 통합검색으로 찾은 후보 표를 사람이 확인한 뒤 재사용 가능한 Semantic Card로 저장하고, Claim의 지역·모집단을 독립 의미축으로 후보 점수와 화면에 반영한다.

## 확정 범위

1. KOSIS 전체 표를 로컬에 전수 Card화하지 않는다.
2. Claim마다 통합검색으로 상위 후보 3개를 찾는다.
3. 후보마다 7축 Card 초안을 만들고, 사용자가 확인·보정한 뒤에만 저장한다.
4. 저장된 Card는 같은 `table_id`의 이후 후보 검색에서 불러와 재사용한다.
5. Claim의 지역과 모집단은 `indicator`와 별도의 필드·점수 항목으로 처리한다.

## 데이터 흐름

```text
Shadow 문장
→ Claim Profile(지표·시점·단위·지역·모집단·비교방식)
→ KOSIS 통합검색 후보 3개
→ 후보별 Semantic Card 초안(7축)
→ 사용자 확인·보정
→ Semantic Card Store 저장
→ 선택 표의 좌표·Snapshot·계산 판정
```

## 저장 원칙

- 후보 탐색 이력은 실행별 감사 기록으로 기존 `KosisCandidateRunStore`에 유지한다.
- 확인된 Card는 실행과 분리된 `KosisSemanticCardStore`에 저장해 성장형 Catalog로 사용한다.
- 자동 추정값에는 출처와 상태를 남긴다. 확인 전에는 성장 Catalog에 저장하지 않는다.
- 기존 근거 객체·Snapshot·Claim 완료 DB의 의미와 데이터는 변경하지 않는다.

## 화면 원칙

- 후보 목록에서 Card의 7축과 Claim 대비 일치/미확정 상태를 표시한다.
- 버튼은 `후보를 근거 입력에 적용` 대신 `Semantic Card 확인·저장`을 중심 동작으로 한다.
- Card 저장 뒤에만 선택 표의 Evidence 조회·Snapshot 단계로 진행한다.
- 상단 상태에는 누적 Card, 이번 실행 신규 Card, 재사용 Card, 검토 대기 Card를 추가한다.

## 성공 기준

- 지역·모집단이 Claim 프로필에 추출되어 화면과 후보 점수 내역에 독립적으로 표시된다.
- 후보 Card 초안은 7축을 가진다.
- 확인 저장된 Card는 DB에 남고 같은 표의 이후 후보에서 재사용된다.
- 자동 후보만으로는 Catalog에 새 Card가 누적되지 않는다.
- 기존 후보 탐색, Snapshot, 판정, Claim 완료 테스트가 유지된다.
