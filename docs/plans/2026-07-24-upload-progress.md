# Upload Progress Status Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show article-registration progress and counts inside the Operations Home area while a CSV upload is being registered.

**Architecture:** Keep the existing synchronous `import_article_file` flow. Add a local `st.status`/placeholder progress panel around each completed stage so the UI reports the current phase and known counts without changing the ingest service API. Keep error handling inside the same panel and preserve the existing upload summary state.

**Tech Stack:** Python 3, Streamlit, pytest.

---

### Task 1: Add the progress-panel UI contract

**Files:**
- Modify: `tests/test_upload_scoped_dashboard.py`

**Step 1: Write the failing tests**

Add assertions scoped to the Operations Home section for the four stage labels (`파일 읽기`, `기사 등록`, `출처 분류`, `검증 후보 준비`) and a progress/status API call.

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

Expected: FAIL because the stage labels and status panel are not yet present.

### Task 2: Render staged progress during article registration

**Files:**
- Modify: `streamlit_app.py`

**Step 1: Implement the smallest UI change**

Inside the existing `기사 등록` handler, create a status container and update it after reading the CSV, importing articles, and calculating the upload summary. Show counts available at each point and mark the final stage complete. Keep the current success message and session-state assignments.

**Step 2: Add failure-state rendering**

When registration raises an existing handled exception, update the status container to a failed state and show the error text in the Operations Home area before retaining the existing error behavior.

**Step 3: Run focused tests**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

Expected: PASS.

### Task 3: Verify and commit

**Files:**
- Modify only: `streamlit_app.py`, `tests/test_upload_scoped_dashboard.py`

**Step 1: Run verification**

Run:

```bash
pytest tests/test_source_classifier.py tests/test_service.py tests/test_upload_scoped_dashboard.py -q
python -m py_compile streamlit_app.py
git diff --check
```

**Step 2: Commit**

```bash
git add streamlit_app.py tests/test_upload_scoped_dashboard.py
git commit -m "feat: show upload progress in operations home"
```
