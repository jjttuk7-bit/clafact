# KOSIS 실제 값 대조 게이트 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KOSIS 실제 값 대조가 기간·지표·선택 조건·값 성격·단위를 모두 확인한 뒤에만 수치를 비교하고, 근거를 Shadow 화면과 CSV에 기록하게 한다.

**Architecture:** `clafact.kosis_value_comparison`에 게이트 결과 모델과 단위·값 성격 판정을 둔다. 비교 함수는 최초 실패 게이트에서 `not_comparable`를 반환하며, 기존 저장소는 결과 JSON을 그대로 보존한다. Streamlit은 저장된 게이트 기록을 표시하고 `shadow_export`는 이를 CSV 열로 평탄화한다.

**Tech Stack:** Python 3, dataclasses, pytest, Streamlit, SQLite JSON payload, CSV.

---

### Task 1: 게이트 결과 모델과 기간·지표·선택 조건 기록

**Files:**
- Modify: `clafact/kosis_value_comparison.py`
- Modify: `tests/test_kosis_value_comparison.py`

**Step 1: Write the failing test**

`tests/test_kosis_value_comparison.py`에 기존 동일 기간 일치 대조가 `gate_results`에서 기간·지표·선택 조건의 통과 기록을 반환한다고 검증한다.

```python
assert [gate["name"] for gate in result.gate_results[:3]] == ["기간", "지표", "선택 조건"]
assert all(gate["passed"] for gate in result.gate_results[:3])
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_kosis_value_comparison.py::test_compares_percent_claim_against_same_period_snapshot_value -q`

Expected: FAIL because `gate_results` does not exist.

**Step 3: Write minimal implementation**

`KosisValueComparison`에 불변 게이트 결과 튜플을 추가하고 `_result`가 이를 직렬화한다. 기간·지표·선택 조건 분기마다 해당 게이트의 통과/실패 근거를 누적한다.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_kosis_value_comparison.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/kosis_value_comparison.py tests/test_kosis_value_comparison.py
git commit -m "feat: record KOSIS value comparison gates"
```

### Task 2: 값 성격·단위 안전 게이트

**Files:**
- Modify: `clafact/kosis_value_comparison.py`
- Modify: `tests/test_kosis_value_comparison.py`

**Step 1: Write the failing test**

문장이 `0.3%p`이고 KOSIS 레코드 단위가 `%`일 때 `not_comparable`이며 값 성격 또는 단위 게이트 실패를 기록한다고 검증한다.

```python
assert result.status == "not_comparable"
assert "값 성격" in result.reason or "단위" in result.reason
assert any(not gate["passed"] for gate in result.gate_results)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_kosis_value_comparison.py::test_does_not_compare_percentage_point_to_percent_rate -q`

Expected: FAIL because `%p`가 `%`와 구분되지 않거나 게이트 기록이 없다.

**Step 3: Write minimal implementation**

문장 `Quantity`와 공식 단위를 비율·퍼센트포인트·절대수치로 분류한다. `%`와 `%p`는 다른 성격으로 취급하고, 절대수치는 단위가 정확히 같은 경우만 통과시킨다. 실패 시 수치 변환 전에 중단한다.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_kosis_value_comparison.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/kosis_value_comparison.py tests/test_kosis_value_comparison.py
git commit -m "feat: gate KOSIS value comparisons by unit type"
```

### Task 3: CSV에 게이트 근거 내보내기

**Files:**
- Modify: `clafact/shadow_export.py`
- Modify: `tests/test_shadow_export.py`

**Step 1: Write the failing test**

게이트 결과를 포함한 비교 객체를 CSV로 내보낼 때 `kosis_value_comparison_gates` 열에 읽을 수 있는 텍스트가 들어간다고 검증한다.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shadow_export.py -q`

Expected: FAIL because CSV 열과 평탄화 로직이 없다.

**Step 3: Write minimal implementation**

CSV 열을 하나 추가하고, `gate_results`를 `게이트: 통과/실패(근거)` 형태로 변환한다. 게이트가 없는 과거 저장 결과에는 빈 값을 유지한다.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shadow_export.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/shadow_export.py tests/test_shadow_export.py
git commit -m "feat: export KOSIS comparison gate reasons"
```

### Task 4: Shadow 화면에 게이트 기록 표시

**Files:**
- Modify: `streamlit_app.py:2453-2505`
- Modify: `tests/test_streamlit_light_surfaces.py` 또는 관련 AppTest

**Step 1: Write the failing test**

실제값 대조 결과가 있을 때 화면에 `대조 게이트`와 게이트별 통과·실패 근거가 표시된다는 최소 AppTest 또는 렌더 문자열 테스트를 추가한다.

**Step 2: Run test to verify it fails**

Run: `python -m pytest <targeted-test> -q`

Expected: FAIL because 게이트 표시가 없다.

**Step 3: Write minimal implementation**

기존 상태·기간·스냅샷·사유 표시 아래에 게이트별 한 줄을 출력한다. 결과가 없거나 과거 결과에 게이트가 없으면 표시하지 않는다.

**Step 4: Run test to verify it passes**

Run: `python -m pytest <targeted-test> -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add streamlit_app.py tests/<targeted-test>.py
git commit -m "feat: show KOSIS comparison gates in Shadow"
```

### Task 5: 통합 검증

**Files:**
- Verify only

**Step 1: Run focused regression suite**

Run:

```bash
python -m pytest tests/test_kosis_value_comparison.py tests/test_kosis_value_comparison_store.py tests/test_kosis_snapshot_compare.py tests/test_shadow_export.py -q
```

Expected: PASS.

**Step 2: Compile Streamlit entry point**

Run: `python -m py_compile streamlit_app.py`

Expected: PASS.

**Step 3: Run relevant AppTest**

Run: `python -m pytest tests/test_streamlit_app.py -q` when present, otherwise run the narrowest existing Streamlit render test.

Expected: PASS or pre-existing documented failure only.

**Step 4: Review diff and status**

Run:

```bash
git diff main...HEAD --check
git status --short
```

Expected: no whitespace errors and only intended changes.

**Step 5: Commit any final test/doc adjustment**

```bash
git add <intended-files>
git commit -m "test: verify KOSIS value comparison gates"
```