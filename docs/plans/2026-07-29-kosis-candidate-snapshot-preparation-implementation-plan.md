# KOSIS 후보 적용 뒤 자동 조회·스냅샷 준비 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow Mode 사용자가 후보 적용 뒤 한 번의 준비 동작으로 공식 KOSIS 조회, 메타데이터 초안, 스냅샷 준비를 끝내고 저장·실제값 대조로 이어가게 한다.

**Architecture:** 기존 `streamlit_app.py`의 자동 채우기 처리와 스냅샷 컨텍스트를 작은 순수 헬퍼로 분리한다. 후보 적용과 수동 입력은 같은 헬퍼를 사용하며, Streamlit은 버튼·상태·오류만 담당한다. 기존 근거 저장 경로는 준비된 컨텍스트를 그대로 저장한다.

**Tech Stack:** Python 3, pytest, Streamlit, KOSIS HTTP API, SQLite research stores.

---

### Task 1: 공식 조회·스냅샷 준비 헬퍼

**Files:**
- Create: `clafact/kosis_snapshot_preparation.py`
- Create: `tests/test_kosis_snapshot_preparation.py`

**Step 1: Write the failing test**

API 행과 고정 조회시각을 전달했을 때, 준비 결과가 자동채움 필드·구조 판정·스냅샷 컨텍스트를 모두 반환한다고 검증한다.

```python
result = prepare_kosis_snapshot_context(
    table_id="DT_CPI", org_id="101", rows=[row], retrieved_at="2026-07-29T10:00:00+09:00"
)
assert result.snapshot_context["table_id"] == "DT_CPI"
assert result.fields.indicator == "전년동월비(%)"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_kosis_snapshot_preparation.py -q`

Expected: FAIL because the module/function does not exist.

**Step 3: Write minimal implementation**

`autofill_from_rows`와 `classify_table_structure`를 호출해 불변 `KosisSnapshotPreparation`을 반환한다. 스냅샷 컨텍스트는 기존 저장 코드가 요구하는 `org_id`, `table_id`, `query_params`, `retrieved_at`, `rows`만 포함한다.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_kosis_snapshot_preparation.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/kosis_snapshot_preparation.py tests/test_kosis_snapshot_preparation.py
git commit -m "feat: prepare KOSIS snapshot context"
```

### Task 2: Shadow 후보 적용 안내와 준비 버튼 연결

**Files:**
- Modify: `streamlit_app.py:1875-2025`
- Modify: `streamlit_app.py:2362-2375`
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write the failing test**

화면 소스에 `KOSIS 조회·스냅샷 준비` 버튼, 준비 완료 안내, 후보 적용 뒤 준비 행동 안내가 포함됨을 검증한다.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: FAIL because 아직 새 버튼·문구가 없다.

**Step 3: Write minimal implementation**

기존 자동 채우기 버튼을 새 명칭으로 바꾸고, 내부에서 `HttpKosisClient.fetch_data` 결과를 새 헬퍼에 전달한다. 성공 시 세션 상태 필드를 채우고 준비 상태를 보여 준다. 실패 시 스냅샷 컨텍스트를 남기지 않는다. 후보 적용 성공 문구를 다음 행동 안내로 바꾼다.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py tests/test_kosis_snapshot_preparation.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_shadow_guide_safety.py
git commit -m "feat: prepare KOSIS snapshots after candidate apply"
```

### Task 3: 통합 검증

**Files:**
- Verify only

**Step 1: Run focused tests**

```bash
python -m pytest tests/test_kosis_evidence_autofill.py tests/test_kosis_evidence_autofill_period.py tests/test_kosis_evidence_autofill_readiness.py tests/test_kosis_evidence_snapshot.py tests/test_kosis_snapshot_preparation.py tests/test_streamlit_shadow_guide_safety.py -q
```

Expected: PASS.

**Step 2: Compile Streamlit entry point**

Run: `python -m py_compile streamlit_app.py`

Expected: PASS.

**Step 3: Review change set**

```bash
git diff main...HEAD --check
git status --short
```

Expected: no whitespace errors and only intended changes.

**Step 4: Commit any final adjustments**

```bash
git add <intended-files>
git commit -m "test: verify KOSIS snapshot preparation"
```