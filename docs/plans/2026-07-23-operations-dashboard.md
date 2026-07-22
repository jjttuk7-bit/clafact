# Operations Dashboard Visual Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restyle the Streamlit operations home as a trustworthy public-data operations console without changing its API or queue behavior.

**Architecture:** Keep data loading and API calls intact. Extract the operations dashboard rendering into small helpers so the UI has one shared visual system, safe database cleanup, and testable claim-row mapping.

**Tech Stack:** Python, Streamlit, pytest.

---

### Task 1: Add a failing claim-row mapping test

**Files:**
- Create: `tests/test_ops_dashboard.py`
- Modify: `streamlit_app.py`

**Step 1: Write the failing test**

```python
def test_build_ops_claim_rows_exposes_readable_status_and_hcx_signal():
    rows = build_ops_claim_rows([
        {"sentence": "실업률은 3.7%다.", "status": "PENDING", "label": None,
         "tier": None, "audit_json": '{"hcx_detection": {"mode": "live"}}', "error": None}
    ])
    assert rows[0]["처리 상태"] == "대기"
    assert rows[0]["HCX 신호"] == "실시간 보조"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ops_dashboard.py -q`

Expected: FAIL because `build_ops_claim_rows` does not exist.

**Step 3: Implement the minimal mapping helper**

Create `build_ops_claim_rows` in `streamlit_app.py`, mapping known service statuses and HCX modes to readable Korean strings while preserving unknown values safely.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ops_dashboard.py -q`

Expected: PASS.

### Task 2: Apply the public-data console visual system

**Files:**
- Modify: `streamlit_app.py:155-205`

**Step 1: Add focused Streamlit styling**

Use `st.markdown` CSS for navy surfaces, teal status accents, coherent cards, visible focus treatment, responsive columns, and readable data-table controls. Scope selectors to the existing Streamlit app.

**Step 2: Restructure only the operations-home presentation**

Render an operations header, metric cards with explicit state copy, a bordered action panel, and an audit-log section. Keep the existing API request URLs, payloads, and timeouts unchanged.

**Step 3: Close the claim-query store reliably**

Use `try`/`finally` around the claim query so its connection is always closed.

### Task 3: Verify the refreshed dashboard

**Files:**
- Test: `tests/test_ops_dashboard.py`
- Test: `tests/api/test_article_import_api.py`
- Test: `streamlit_app.py`

**Step 1: Run focused tests**

Run: `pytest tests/test_ops_dashboard.py tests/api/test_article_import_api.py -q`

Expected: PASS.

**Step 2: Check application syntax**

Run: `python -m py_compile streamlit_app.py`

Expected: exit code 0.

**Step 3: Run the full offline suite**

Run: `pytest`

Expected: all non-live tests pass.

**Step 4: Inspect the local Streamlit page**

Run Streamlit locally and verify the operations home at desktop and narrow viewport widths; confirm both buttons remain visible and the audit table is legible.
