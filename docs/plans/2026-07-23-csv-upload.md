# CSV Article Upload Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow operations users to upload a CSV article file, register it through the existing ingest pipeline, and separately choose when to process queued claims.

**Architecture:** Add a multipart FastAPI upload endpoint that writes an upload to a temporary CSV file and delegates to `import_article_file`; always remove the temporary file. Replace the dashboard's server-path input with `st.file_uploader` and send multipart data to the new endpoint.

**Tech Stack:** Python, FastAPI, Streamlit, pytest.

---

### Task 1: Add a failing upload API test

**Files:**
- Modify: `tests/api/test_article_import_api.py`
- Modify: `backend/app/main.py`

**Step 1:** Write a multipart CSV upload test that asserts a successful response and one PENDING claim.

**Step 2:** Run the focused test and verify it fails because the endpoint does not exist.

### Task 2: Implement temporary CSV upload handling

**Files:**
- Modify: `backend/app/main.py`

**Step 1:** Add an `UploadFile` endpoint accepting only `.csv`.

**Step 2:** Save bytes to `NamedTemporaryFile`, call the existing import service, then remove the file in `finally`.

**Step 3:** Map parser and file errors to an HTTP 400 response.

**Step 4:** Run the focused API test and verify it passes.

### Task 3: Replace path entry with dashboard uploader

**Files:**
- Modify: `streamlit_app.py`

**Step 1:** Replace the server-path text input with `st.file_uploader` accepting CSV.

**Step 2:** Send the selected file to the upload endpoint with multipart encoding and show registration counts.

**Step 3:** Keep the existing batch processing control separate.

### Task 4: Verify

**Files:**
- Test: `tests/api/test_article_import_api.py`
- Test: `streamlit_app.py`

**Step 1:** Run `python -m py_compile streamlit_app.py backend/app/main.py`.

**Step 2:** Run `pytest`.
