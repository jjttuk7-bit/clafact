# Shadow CSV KOSIS 근거 연결 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow 실행 CSV의 각 문장 행에 저장된 KOSIS 근거 연결·적합도 정보를 함께 내보낸다.

**Architecture:** `KosisShadowMappingStore`의 연구 전용 매핑을 실행 ID와 행 번호로 조회·그룹화한 뒤, 기존 `export_shadow_run_csv`가 만드는 행에 병합한다. 매핑이 없거나 저장소를 읽을 수 없을 때도 기존 CSV 다운로드는 유지하며 KOSIS 열만 빈 값으로 남긴다.

**Tech Stack:** Python 3, SQLite, pytest, Streamlit.

---

### Task 1: CSV 병합 함수의 실패 테스트 작성

**Files:**
- Modify: `tests/test_shadow_export.py`
- Modify: `clafact/shadow_export.py`

**Step 1: Write the failing test**

`export_shadow_run_csv`에 `mappings_by_row`를 전달했을 때, 한 행에 `kosis_table_id`, 상태, 점수, 사유, 선택 조건, 메모가 포함되는 테스트를 작성한다. 복수 매핑은 ` | `로 연결되는지 확인한다.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_export.py -q`

Expected: 새 인자를 지원하지 않거나 새 열이 없어 FAIL.

**Step 3: Write minimal implementation**

`SHADOW_CSV_COLUMNS`에 KOSIS 열을 추가하고, 선택적 `mappings_by_row`를 받아 행별 값을 안전하게 평탄화한다. 기존 호출자는 인자를 생략할 수 있어야 한다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shadow_export.py -q`

Expected: PASS.

### Task 2: Streamlit 다운로드에 연구 매핑 연결

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_streamlit_shadow_csv_kosis.py`

**Step 1: Write the failing test**

실행 ID가 있는 Shadow CSV 다운로드 경로가 `KosisShadowMappingStore.list_for_run` 결과를 `export_shadow_run_csv`에 전달하는지를 검증한다.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_streamlit_shadow_csv_kosis.py -q`

Expected: KOSIS 연결 정보가 다운로드 CSV에 없어 FAIL.

**Step 3: Write minimal implementation**

다운로드 직전에 연구 저장소를 읽어 `row_index`별 매핑 사전을 만들고 CSV 내보내기 함수에 전달한다. 실패 시 사용자에게 경고를 보여 주되 다운로드는 계속 가능하게 한다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_streamlit_shadow_csv_kosis.py -q`

Expected: PASS.

### Task 3: 회귀 검증과 커밋

**Files:**
- Verify: `tests/test_shadow_export.py`
- Verify: `tests/test_kosis_shadow_mapping_store.py`
- Verify: `tests/test_streamlit_shadow_csv_kosis.py`

**Step 1: Run focused regression tests**

Run: `pytest tests/test_shadow_export.py tests/test_kosis_shadow_mapping_store.py tests/test_streamlit_shadow_csv_kosis.py -q`

Expected: PASS.

**Step 2: Run Streamlit AppTest**

Run: `pytest tests/test_streamlit_shadow_csv_kosis.py -q`

Expected: PASS without app exception.

**Step 3: Commit**

```powershell
git add clafact/shadow_export.py streamlit_app.py tests/test_shadow_export.py tests/test_streamlit_shadow_csv_kosis.py docs/plans/2026-07-28-shadow-csv-kosis-link-design.md docs/plans/2026-07-28-shadow-csv-kosis-link-implementation.md
git commit -m "feat: export KOSIS links with shadow CSV"
```
