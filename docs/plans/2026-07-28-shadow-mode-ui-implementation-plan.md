# Shadow Mode UI Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** 기존 검증 실험실에 연구 전용 Shadow Mode 탭을 추가해 실행, 결과 확인, 사람 검토, JSON·CSV 다운로드를 제공한다.

**Architecture:** `streamlit_app.py`는 화면과 세션 상태만 담당하고 `shadow_ui.py`의 순수 보조 함수와 `ShadowLabService`를 호출한다. 모든 Shadow 결과는 `data/research/shadow_lab.db`에만 저장하며, 운영 저장소와 기존 비교 실험 저장소는 변경하지 않는다.

**Tech Stack:** Python 3.11, Streamlit, SQLite, pytest.

---

### Task 1: Shadow UI 보조 함수

**Files:** Create `clafact/shadow_ui.py`; Test `tests/test_shadow_ui.py`.

1. `shadow_database_path`, `validate_shadow_input`, `summary_metrics`의 실패 테스트를 작성한다.
2. `pytest tests/test_shadow_ui.py -v`로 모듈 부재 실패를 확인한다.
3. 연구 전용 경로, 빈 본문 오류, 안전한 숫자 요약만 최소 구현한다.
4. 같은 테스트가 통과하는지 확인한다.

### Task 2: Streamlit Shadow 탭 렌더러

**Files:** Modify `streamlit_app.py`; modify `clafact/shadow_ui.py`; test `tests/test_shadow_ui.py`.

1. 저장 실행을 화면용으로 평탄화하는 `shadow_result_rows`의 실패 테스트를 작성한다.
2. `pytest tests/test_shadow_ui.py::test_shadow_result_rows_flattens_saved_run_for_display -v`로 실패를 확인한다.
3. 기존 `검증 실험실`을 `기존 비교 실험`, `Shadow Mode` 탭으로 나눈다. 첫 탭의 코드는 그대로 보존한다.
4. Shadow 탭에 본문·발행일·실행 버튼, 요약 metric, 결과 dataframe을 추가한다.
5. UI 보조 함수 테스트가 통과하는지 확인한다.

### Task 3: 검토·내보내기 연결

**Files:** Modify `streamlit_app.py`; modify `clafact/shadow_ui.py`; test `tests/test_shadow_ui.py`.

1. `download_filenames(run_id)`의 실패 테스트를 작성한다.
2. 실행 결과가 있을 때에만 승인·보정·보류, 메모, `ShadowLabService.review` 연결을 추가한다.
3. 저장 후 실행을 다시 조회하고 JSON·CSV `st.download_button`을 제공한다.
4. 파일명과 데이터 준비 테스트를 통과시킨다.

### Task 4: 회귀 검증과 변경 기록

**Files:** Modify `docs/SHADOW_LAB_CHANGELOG.md`; test all Shadow modules and existing experiment tests.

1. 다음 명령을 실행한다.

```bash
pytest tests/test_shadow_policy.py tests/test_shadow_store.py tests/test_shadow_runner.py tests/test_shadow_service.py tests/test_shadow_export.py tests/test_shadow_ui.py tests/test_experiment_lab.py tests/test_experiment_export.py -v
```

2. `streamlit run streamlit_app.py`로 두 탭, Shadow 실행·검토·다운로드, 연구 전용 경로만 사용하는지 수동 확인한다.
3. 변경 이력에 UI 탭·운영 영향 없음·검증 결과를 기록한다.
4. 문서와 구현을 개별 커밋한다.
