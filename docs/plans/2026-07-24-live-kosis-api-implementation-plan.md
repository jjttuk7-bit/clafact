# Live KOSIS API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use real KOSIS Open API search and data retrieval from the Streamlit verification UI.

**Architecture:** Replace the fixture-only engine returned by `load_engine()` with `HttpKosisClient` plus `KosisSearchIndex`; keep existing rate limiting, budget, retries, and masked audit URLs.

**Tech Stack:** Python, Streamlit, KOSIS Open API, pytest.

---

### Task 1: Add a live-engine wiring regression test

**Files:**
- Modify: `tests/test_upload_scoped_dashboard.py`

1. Add a source test asserting `HttpKosisClient`, `KosisSearchIndex`, and `KOSIS_API_KEY` are used by the Streamlit engine.
2. Run `pytest tests/test_upload_scoped_dashboard.py -q` and confirm it fails for missing live wiring.

### Task 2: Wire real KOSIS search and retrieval

**Files:**
- Modify: `streamlit_app.py`

1. Import `HttpKosisClient` and `KosisSearchIndex`.
2. Make `load_engine()` construct `HttpKosisClient(api_key=os.environ["KOSIS_API_KEY"])` and `KosisSearchIndex(client)`.
3. Keep the existing button error handling and do not expose the key.
4. Run the targeted test and confirm it passes.

### Task 3: Verify and commit

Run:

```bash
python -m py_compile streamlit_app.py
pytest tests/test_upload_scoped_dashboard.py tests/test_retrieve_kosis.py tests/test_throttle.py tests/test_service.py -q
git diff --check
```

Commit the source, test, and plan with `feat: use live KOSIS API in dashboard`.
