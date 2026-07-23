# Safe KOSIS Reclassification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reclassify all stored claims under the safer KOSIS policy and make the UI distinguish automatic verification from human review.

**Architecture:** Add a store-level reclassification operation that recomputes source labels and moves only direct domestic KOSIS claims to the pending queue. Preserve prior results in audit JSON when a claim changes route. The Streamlit UI invokes this operation and displays aggregated unverifiable reasons.

**Tech Stack:** Python 3, SQLite, pytest, Streamlit.

---

### Task 1: Define automatic-verification eligibility

**Files:**
- Modify: `clafact/pipeline/source_classify.py`
- Test: `tests/test_source_classifier.py`

**Step 1: Write the failing test**

```python
def test_complex_kosis_claim_requires_human_review():
    label = classify("소비자물가지수는 117.42(2020년=100)다.")
    assert label.route == "HUMAN_REVIEW"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_source_classifier.py::test_complex_kosis_claim_requires_human_review -q`

**Step 3: Implement minimal policy**

Route `KOSIS_BUT_COMPLEX` to `HUMAN_REVIEW`, keeping its source type for auditability.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_source_classifier.py -q`

### Task 2: Reclassify persisted claims safely

**Files:**
- Modify: `clafact/service/store.py`
- Test: `tests/test_service.py`

**Step 1: Write failing tests**

```python
def test_reclassify_moves_complex_done_claim_to_human_review_and_keeps_audit():
    stats = store.reclassify_all_claims()
    assert row["route"] == "HUMAN_REVIEW"
    assert row["status"] == "CLASSIFIED"
    assert previous["label"] == "unverifiable"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_service.py::test_reclassify_moves_complex_done_claim_to_human_review_and_keeps_audit -q`

**Step 3: Implement minimal operation**

Skip reviewer-confirmed claims, recompute classification for all others, save previous result under `reclassification.previous_result`, clear active result fields only when route/status changes, and return route counts.

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_service.py -q`

### Task 3: Show safe-policy controls and verdict-reason metrics

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_upload_scoped_dashboard.py`

**Step 1: Write failing tests**

```python
def test_operations_home_offers_safe_policy_reclassification():
    assert "전체 새 정책 적용" in home

def test_verification_tab_shows_unverifiable_reason_summary():
    assert "판단불가 사유" in verification_section
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

**Step 3: Implement minimal UI**

Add a safe-policy reclassification button to Operations Home and show grouped unresolved reasons in Verification for the current upload.

**Step 4: Run tests to verify pass**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`

### Task 4: Full verification and commit

**Files:**
- Modify: only files from Tasks 1–3

**Step 1: Run focused suites**

Run: `pytest tests/test_source_classifier.py tests/test_service.py tests/test_upload_scoped_dashboard.py -q`

**Step 2: Run syntax check**

Run: `python -m py_compile streamlit_app.py clafact/service/store.py clafact/pipeline/source_classify.py`

**Step 3: Review change scope**

Run: `git diff --check && git status --short`

**Step 4: Commit**

```bash
git add clafact/pipeline/source_classify.py clafact/service/store.py streamlit_app.py tests/test_source_classifier.py tests/test_service.py tests/test_upload_scoped_dashboard.py docs/plans/2026-07-23-safe-kosis-reclassification.md
git commit -m "feat: reclassify claims for safe kosis automation"
```
