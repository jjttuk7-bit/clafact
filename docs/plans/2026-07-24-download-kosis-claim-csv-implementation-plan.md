# KOSIS Claim CSV Download Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let an operator download the current upload's KOSIS numeric-claim extraction table as an Excel-compatible CSV file.

**Architecture:** Reuse the existing `extraction_rows` list built from `upload["claim_previews"]`. Convert that list in memory with the standard-library `csv` module and expose the bytes through Streamlit's `st.download_button` directly below the existing dataframe.

**Tech Stack:** Python standard library (`csv`, `io`, `datetime`), Streamlit, pytest.

---

### Task 1: Add the CSV download regression test

**Files:**
- Modify: `tests/test_upload_scoped_dashboard.py`

**Step 1: Write the failing test**

Add a source-level test that scopes the assertion to the 운영 홈 section and checks for:

```python
assert "st.download_button" in home
assert 'data=csv_buffer.getvalue().encode("utf-8-sig")' in home
assert 'mime="text/csv"' in home
assert "for row in extraction_rows" in home
```

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

Expected: FAIL because the CSV buffer and download button do not yet exist.

### Task 2: Export the existing extraction rows as CSV

**Files:**
- Modify: `streamlit_app.py:10-15`
- Modify: `streamlit_app.py:425-445`

**Step 1: Add standard-library imports**

Add `csv`, `io`, and `datetime` alongside the existing Python standard-library imports.

**Step 2: Build the in-memory CSV after the dataframe**

Inside `if claim_previews:`, immediately after rendering `st.dataframe(extraction_rows, ...)`, create a `StringIO`, initialize a `csv.DictWriter` with the first row's keys, write the header and rows, then render:

```python
st.download_button(
    "추출 결과 CSV 다운로드",
    data=csv_buffer.getvalue().encode("utf-8-sig"),
    file_name=f"clafact_kosis_claims_{datetime.now():%Y%m%d}.csv",
    mime="text/csv",
    use_container_width=True,
)
```

**Step 3: Run the targeted test**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

Expected: PASS.

### Task 3: Verify and commit the feature

**Files:**
- Verify: `streamlit_app.py`
- Verify: `tests/test_upload_scoped_dashboard.py`

**Step 1: Compile and run related regression tests**

Run:

```bash
python -m py_compile streamlit_app.py
pytest tests/test_upload_scoped_dashboard.py tests/test_ingest_observability.py tests/test_source_classifier.py tests/test_service.py -q
```

Expected: PASS, allowing explicitly skipped tests.

**Step 2: Inspect the diff**

Run: `git diff --check`

Expected: no output.

**Step 3: Commit**

```bash
git add streamlit_app.py tests/test_upload_scoped_dashboard.py docs/plans/2026-07-24-download-kosis-claim-csv-implementation-plan.md
git commit -m "feat: add KOSIS claim CSV download"
```
