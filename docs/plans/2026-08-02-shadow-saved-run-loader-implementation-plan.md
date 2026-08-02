# Shadow 저장 실행 불러오기 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 최근 20개 저장 Shadow 실행 중 하나를 현재 화면의 대상으로 불러온다.

**Architecture:** 기존 `ShadowLabService.list_runs(limit=20)`을 읽기 전용으로 사용한다. 선택 상자는 `st.session_state["shadow_lab_run_id"]`만 바꾸며, 이후의 화면은 기존 실행 조회·근거·Claim 완료·CSV 코드를 재사용한다.

**Tech Stack:** Python, Streamlit, pytest.

---

### Task 1: 저장 실행 선택 화면 계약

**Files:**
- Modify: `tests/test_streamlit_claim_completion_contract.py`

**Step 1: Write the failing test**

```python
def test_shadow_screen_can_load_one_of_the_recent_twenty_saved_runs():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    assert "list_runs(limit=20)" in source
    assert '"저장된 Shadow 실행 불러오기"' in source
    assert 'st.session_state["shadow_lab_run_id"]' in source
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_claim_completion_contract.py -q`

Expected: FAIL because the loader label is absent.

**Step 3: Implement minimal UI**

Before loading `shadow_lab_run_id`, fetch `ShadowLabService.list_runs(limit=20)`. Render a selectbox with run time, shortened run ID, and sentence count. On selection, set `st.session_state["shadow_lab_run_id"]` and rerun. Do not write to any store.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_streamlit_claim_completion_contract.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_claim_completion_contract.py
git commit -m "feat: load saved Shadow runs"
```

### Task 2: 실제 사례 확인

**Files:**
- Modify: `C:/Users/USER/Desktop/클라비_아이펠톤/ClaFact_완성형_핵심작업기록/03_검증완료_단순수치_Claim_3건.md`

**Step 1: Run focused checks**

Run: `python -m pytest tests/test_streamlit_claim_completion_contract.py tests/test_claim_completion_store.py tests/test_claim_completion_from_evidence.py tests/test_shadow_export.py -q`

Expected: PASS.

**Step 2: Verify one live case**

Select the prepared `DT_1EA1019` run, click `Claim 완료`, download CSV, and confirm verdict `match`, snapshot ID, and reproducible URL are the same in screen record and CSV.

**Step 3: Update only the core work record**

Append the observed live evidence and next recommendation.
