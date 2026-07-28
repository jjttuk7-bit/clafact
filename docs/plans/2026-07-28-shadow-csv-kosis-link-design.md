# Shadow CSV KOSIS 근거 연결 설계

## 목적

Shadow 실행 CSV의 문장 행을 유지한 채, 해당 문장에 기록된 KOSIS 근거 연결을 함께 내보낸다. 이를 통해 뉴스 문장 분류 실험과 KOSIS 통계표 매핑 실험을 하나의 분석 파일에서 비교할 수 있다.

## 선택한 방식

문장당 한 행을 유지하는 병합 방식이다. 같은 문장에 여러 KOSIS 근거 연결이 있으면 각 값을 ` | `로 연결한다. 이는 기존 행 수·리뷰 집계를 바꾸지 않으며 Excel에서 바로 필터링할 수 있다.

## 데이터 흐름

1. `KosisShadowMappingStore`에서 `shadow_run_id` 기준 매핑을 읽는다.
2. `row_index` 기준으로 그룹화한다.
3. `export_shadow_run_csv`가 각 Shadow 문장 행에 KOSIS 열을 추가한다.
4. 매핑이 없는 문장은 빈 칸으로 남긴다. 운영 Claim·리뷰·판정 데이터는 수정하지 않는다.

## CSV 열

- `kosis_table_id`: 연결된 표 ID
- `kosis_evidence_object_id`: 현재 표 ID와 동일한 근거 객체 식별자
- `kosis_mapping_status`: candidate/reviewed/rejected 상태
- `kosis_match_score`: 문장-표 적합도 점수
- `kosis_match_reasons`: 적합·불일치 사유
- `kosis_source_selection`: 저장된 조회 선택 조건
- `kosis_mapping_note`: 연구 메모

## 오류 처리와 검증

매핑 저장소가 없거나 읽기 실패하면 기존 Shadow CSV를 그대로 생성하되 KOSIS 열은 빈 값으로 남긴다. 단위 테스트는 매핑 없음, 단일 매핑, 복수 매핑 및 Excel 수식 주입 방지 값을 확인한다. Streamlit 화면 테스트는 다운로드 버튼이 확장된 CSV 바이트를 생성하는지 확인한다.
