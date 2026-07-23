# Light Theme Surfaces Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give light and system themes distinct page, card, input, and border surfaces while preserving readable buttons and dark-mode contrast.

**Architecture:** Define dashboard-specific CSS custom properties with a light default and a `prefers-color-scheme: dark` override. Existing Streamlit controls consume the same surface tokens.

**Tech Stack:** Python, Streamlit, pytest.

---

### Task 1: Add a failing palette contract test

**Files:**
- Modify: `tests/test_streamlit_theme_contract.py`
- Modify: `streamlit_app.py`

**Step 1:** Assert the source contains the light page, surface, and border tokens plus a dark media-query override.

**Step 2:** Run `pytest tests/test_streamlit_theme_contract.py -q` and verify it fails.

### Task 2: Define and consume theme surface tokens

**Files:**
- Modify: `streamlit_app.py:155-190`

**Step 1:** Add `--ops-page`, `--ops-surface`, `--ops-border`, `--ops-text`, and `--ops-muted` for the approved light palette.

**Step 2:** Add the dark palette under `@media (prefers-color-scheme: dark)`.

**Step 3:** Use those tokens for page background, inputs, cards, hero, tables, and buttons.

**Step 4:** Re-run the focused test and verify it passes.

### Task 3: Verify the change

**Files:**
- Test: `tests/test_streamlit_theme_contract.py`
- Test: `streamlit_app.py`

**Step 1:** Run `python -m py_compile streamlit_app.py`.

**Step 2:** Run `pytest`.
