# Operations Home Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Streamlit Operations Home readability by grouping registration actions, progress, metrics, and next steps into distinct visual sections.

**Architecture:** Keep the existing upload and classification data flow. Refactor only the Operations Home markup and CSS tokens in `streamlit_app.py`, using existing session state and upload summary values. Add source-level UI contract tests for the new hierarchy and labels.

**Tech Stack:** Python 3, Streamlit, pytest, CSS.

---

### Task 1: Define the redesigned layout contract

**Files:**
- Modify: `tests/test_upload_scoped_dashboard.py`

**Step 1: Write failing tests**

Assert that Operations Home contains a registration card, a primary article-registration action, four summary metric labels, three route result labels, and a next-action section.

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

Expected: FAIL for the new layout selectors or labels.

### Task 2: Implement the visual hierarchy

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Add scoped CSS tokens**

Add styles for the registration card, metric cards, route cards, and next-action callout with clear contrast and spacing.

**Step 2: Restructure Operations Home markup**

Group the uploader, registration button, progress status, and upload completion message inside the registration card. Keep the existing data values and route calculations.

**Step 3: Render summary and route cards**

Use four metric cards for source rows, valid articles, numeric claims, and KOSIS analysis targets. Use three route cards for automatic verification, complex KOSIS review, and separate evidence review.

**Step 4: Run focused tests**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

Expected: PASS.

### Task 3: Verify and commit

**Step 1: Run verification**

```bash
pytest tests/test_source_classifier.py tests/test_service.py tests/test_upload_scoped_dashboard.py tests/test_ingest_observability.py -q
python -m py_compile streamlit_app.py
git diff --check
```

**Step 2: Commit and push**

```bash
git add streamlit_app.py tests/test_upload_scoped_dashboard.py
git commit -m "feat: improve operations home readability"
git push origin main
```
