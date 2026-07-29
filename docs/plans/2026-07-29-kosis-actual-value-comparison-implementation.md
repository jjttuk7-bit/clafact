# KOSIS 실제 수치 대조 구현 계획

> **실행 방식:** 현재 세션에서 순차 구현·검증한다. 운영 판정과 분리된 Shadow 연구 저장소만 변경한다.

## 1. 대조 도메인 모델과 단위 테스트

**파일:** `clafact/kosis_value_comparison.py`, `tests/test_kosis_value_comparison.py`

1. 먼저 퍼센트·정수 수치 정규화, 기간 정규화, 스냅샷 행 선택 실패 테스트를 작성한다.
2. `KosisValueComparison`과 `compare_claim_to_snapshot`을 구현한다.
3. 일치·불일치·비교 불가와 판정 근거를 모두 테스트한다.

## 2. 불변 연구 기록 저장소

**파일:** `clafact/kosis_value_comparison_store.py`, `tests/test_kosis_value_comparison_store.py`

1. 실행·문장·근거 객체·스냅샷 조합으로 비교 기록을 저장한다.
2. 동일 ID·동일 payload 재저장은 허용하고, 내용이 다른 충돌은 거부한다.
3. 실행 및 근거 객체 기준 조회를 테스트한다.

## 3. Shadow 화면 연결

**파일:** `streamlit_app.py`, `clafact/shadow_export.py`, 관련 UI 테스트

1. 현재 문장과 선택 근거의 최신 스냅샷을 찾아 "실제 값 대조" 버튼을 제공한다.
2. 주장값·공식값·스냅샷 시각·판정·상세 이유를 표시한다.
3. 비교 결과를 Shadow 전용 저장소에만 기록하고 JSON/CSV 내보내기에 포함한다.

## 4. 검증 및 배포

1. 관련 단위 테스트를 실행한다.
2. `py_compile`과 Streamlit `AppTest`로 import·초기 렌더링을 검증한다.
3. 변경 사항을 커밋하고 feature/main에 푸시한다.
