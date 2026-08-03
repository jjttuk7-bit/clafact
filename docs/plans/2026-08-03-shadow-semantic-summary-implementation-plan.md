# Shadow Semantic Summary Cards Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show actual Shadow-run semantic verification status and persisted Golden Set E2E status in Streamlit without changing the existing verification or export contracts.

**Architecture:** Add pure aggregation helpers to `clafact.shadow_ui`, then render their results in two small Streamlit metric groups. The helpers consume existing run/store records and the persisted E2E JSON list; no new database or mock data is introduced.

**Tech Stack:** Python, pytest, Streamlit.

---

### Task 1: Current-run summary helper

**Files:**
- Modify: `clafact/shadow_ui.py`
- Modify: `tests/test_shadow_ui.py`

**Step 1:** Add a failing test for candidate/search/mapping/comparison/verdict/completed-Claim aggregation.

**Step 2:** Run the focused pytest test and confirm the missing helper fails.

**Step 3:** Add the smallest pure `current_semantic_summary` implementation.

**Step 4:** Re-run the focused test and confirm it passes.

### Task 2: Golden Set E2E summary helper

**Files:**
- Modify: `clafact/shadow_ui.py`
- Modify: `tests/test_shadow_ui.py`

**Step 1:** Add a failing test with multiple component verdicts for one candidate and snapshot/non-snapshot records.

**Step 2:** Run the focused pytest test and confirm failure.

**Step 3:** Add `e2e_semantic_summary` with candidate-level deduplication and safe defaults.

**Step 4:** Re-run the focused test and confirm it passes.

### Task 3: Streamlit rendering and regression verification

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_shadow_ui.py`, `tests/test_e2e_shadow.py`, existing Shadow export and Claim-completion tests

**Step 1:** Load the existing research records once for both the guide and the summary cards.

**Step 2:** Render the two metric groups only when a Shadow run is open; render a transparent unavailable message for absent E2E JSON.

**Step 3:** Keep existing Claim completion and CSV assembly unchanged except for reusing loaded values.

**Step 4:** Run focused tests, full relevant regression tests, and `python -m py_compile streamlit_app.py`.

**Step 5:** Stage only the feature files, commit, push, and verify the remote branch.
