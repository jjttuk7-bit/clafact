# Sidebar Navigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the top tab navigation with a responsive left sidebar while preserving every existing ClaFact workflow.

**Architecture:** Use a Streamlit radio control in `st.sidebar` as the single navigation state. Guard each existing section with the matching selected label instead of `st.tabs`; render the same radio horizontally at small viewport widths through CSS only if necessary.

**Tech Stack:** Python, Streamlit, pytest.

---

### Task 1: Add a failing navigation contract test

**Files:**
- Create: `tests/test_sidebar_navigation.py`
- Modify: `streamlit_app.py`

**Step 1:** Assert the source creates a sidebar navigation control with all five labels and no longer calls `st.tabs`.

**Step 2:** Run `pytest tests/test_sidebar_navigation.py -q` and verify it fails.

### Task 2: Replace tabs with sidebar navigation

**Files:**
- Modify: `streamlit_app.py:190-420`

**Step 1:** Add the sidebar brand block and navigation radio control.

**Step 2:** Replace each `with tab_*:` block with a selected-label conditional without changing the existing workflow body.

**Step 3:** Add sidebar, active state, and mobile CSS using the current `--ops-*` surface tokens.

**Step 4:** Run the focused navigation contract test and verify it passes.

### Task 3: Verify workflow preservation

**Files:**
- Test: `tests/test_sidebar_navigation.py`
- Test: `streamlit_app.py`

**Step 1:** Run `python -m py_compile streamlit_app.py`.

**Step 2:** Run `pytest`.
