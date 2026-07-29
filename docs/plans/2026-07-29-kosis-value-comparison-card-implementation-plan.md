# KOSIS 실제 값 비교 카드 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow Mode에서 KOSIS 실제 값 대조 결과와 스냅샷 후보를 읽기 쉬운 비교 카드로 표시한다.

**Architecture:** 순수 `clafact.kosis_value_comparison_card` 모듈이 비교 결과와 스냅샷을 카드 모델로 변환한다. Streamlit은 기존 실제 값 대조 저장 후 해당 모델을 읽어 카드·게이트·후보 expander를 렌더링한다. 기존 비교·저장 로직은 변경하지 않는다.

**Tech Stack:** Python 3, dataclasses, pytest, Streamlit.

---

### Task 1: 비교 카드 모델 만들기

**Files:**
- Create: `clafact/kosis_value_comparison_card.py`
- Create: `tests/test_kosis_value_comparison_card.py`

**Step 1: Write the failing test**

```python
def test_builds_primary_card_with_compared_official_record_first():
    card = build_value_comparison_card(comparison, snapshot)
    assert card.primary.official_value == "2.4%"
    assert card.alternatives[0].period == "2025-10"
```

**Step 2: Run the test**

Run: `python -m pytest tests/test_kosis_value_comparison_card.py -q`

Expected: FAIL because `build_value_comparison_card` does not exist.

**Step 3: Write the minimal implementation**

- Define frozen card and candidate dataclasses.
- Normalize periods with the format used by `kosis_value_comparison`.
- Match the comparison's official value/period first, then rank remaining records by period, indicator, selection, and unit compatibility.

**Step 4: Verify green**

Run: `python -m pytest tests/test_kosis_value_comparison_card.py -q`

Expected: PASS.

**Step 5: Add failure-path tests**

- Assert `not_comparable` cards expose the existing reason and no false primary record.
- Assert an empty snapshot produces no alternatives.

**Step 6: Commit**

```bash
git add clafact/kosis_value_comparison_card.py tests/test_kosis_value_comparison_card.py
git commit -m "feat: build KOSIS value comparison cards"
```

### Task 2: Shadow Mode에 카드 렌더링 연결하기

**Files:**
- Modify: `streamlit_app.py:2457-2518`
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write the failing source-contract test**

```python
def test_shadow_actual_value_comparison_renders_card_and_alternatives():
    assert 'KOSIS 실제 값 비교' in source
    assert '다른 공식 값 후보 보기' in source
    assert 'build_value_comparison_card' in source
```

**Step 2: Run the test**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: FAIL because the card renderer does not exist.

**Step 3: Write the minimal implementation**

- Import the card builder.
- After `comparison_display` is loaded, build a card using the same `latest_snapshot`.
- Render status, sentence/KOSIS values, source period·indicator·selection, snapshot ID·retrieved time, and gate details.
- Render `st.expander("다른 공식 값 후보 보기")` only when alternatives exist.
- Do not create a store write or modify mapping/review controls.

**Step 4: Run focused tests**

Run: `python -m pytest tests/test_kosis_value_comparison_card.py tests/test_streamlit_shadow_guide_safety.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_shadow_guide_safety.py
git commit -m "feat: show KOSIS value comparison card"
```

### Task 3: 통합 검증

**Files:**
- Test: `tests/test_kosis_value_comparison.py`
- Test: `tests/test_kosis_value_comparison_store.py`
- Test: `tests/test_kosis_snapshot_preparation.py`
- Test: `tests/test_kosis_value_comparison_card.py`
- Test: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Run focused verification**

```bash
python -m pytest tests/test_kosis_value_comparison.py tests/test_kosis_value_comparison_store.py tests/test_kosis_snapshot_preparation.py tests/test_kosis_value_comparison_card.py tests/test_streamlit_shadow_guide_safety.py -q
python -m py_compile streamlit_app.py
git diff main...HEAD --check
```

Expected: all tests pass, compilation succeeds, and diff check is clean.

**Step 2: Run full verification**

Run: `python -m pytest -q`

Expected: all tests pass.
