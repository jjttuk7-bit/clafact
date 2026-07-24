# KOSIS Transient Retry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KOSIS 연결 시간 초과 Claim을 예약 재시도하고, 화면에는 안전하고 간결한 안내를 표시한다.

**Architecture:** `HttpKosisClient`는 연결 실패를 전용 예외로 표시한다. 서비스 배치는 그 예외만 SQLite 재시도 메타데이터와 함께 PENDING으로 예약하고, 큐 조회는 예약 시각 이후에만 반환한다. Streamlit은 원문 traceback 대신 재시도 가능 시각을 표시한다.

**Tech Stack:** Python 3 stdlib, SQLite, Streamlit, pytest.

---

### Task 1: KOSIS 연결 실패를 전용 예외로 구분

**Files:**
- Modify: `clafact/kosis.py:167-225`
- Test: `tests/test_throttle.py`

**Step 1: Write the failing test**

```python
def test_kosis_connection_error_is_retryable():
    error = KosisConnectionError("timed out")
    assert isinstance(error, RuntimeError)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_throttle.py::test_kosis_connection_error_is_retryable -q`

Expected: FAIL because `KosisConnectionError` does not exist.

**Step 3: Write minimal implementation**

Add `KosisConnectionError(RuntimeError)` and raise it from the final `URLError`/`TimeoutError` branch in `HttpKosisClient._call`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_throttle.py::test_kosis_connection_error_is_retryable -q`

**Step 5: Commit**

```bash
git add clafact/kosis.py tests/test_throttle.py
git commit -m "feat: classify KOSIS connection failures"
```

### Task 2: Store and defer retryable Claims

**Files:**
- Modify: `clafact/service/store.py:42-215,376-388`
- Test: `tests/test_service.py`

**Step 1: Write failing tests**

```python
def test_schedule_kosis_retry_defers_claim_until_due():
    store = _store()
    # enqueue one KOSIS Claim
    store.schedule_kosis_retry("clm", "timeout", now="2026-07-25T10:00:00")
    assert store.fetch_pending(now="2026-07-25T10:01:00") == []
    assert store.fetch_pending(now="2026-07-25T10:03:00")[0]["claim_id"] == "clm"

def test_schedule_kosis_retry_stops_after_three_attempts():
    # three scheduled retries leave the Claim FAILED with failure_kind retained
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_service.py::test_schedule_kosis_retry_defers_claim_until_due tests/test_service.py::test_schedule_kosis_retry_stops_after_three_attempts -q`

**Step 3: Write minimal implementation**

- Add `retry_count`, `next_retry_at`, and `failure_kind` to the schema and migration map.
- Add `schedule_kosis_retry` with a 2-minute delay and a maximum of three scheduled attempts.
- Make `fetch_pending` accept an optional `now` value and select only Claims whose `next_retry_at` is empty or due.
- Reset retry metadata in successful saves and explicit manual retry.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_service.py -q`

**Step 5: Commit**

```bash
git add clafact/service/store.py tests/test_service.py
git commit -m "feat: defer transient KOSIS retries"
```

### Task 3: Schedule only transient KOSIS failures in the batch

**Files:**
- Modify: `clafact/service/batch.py:65-96`
- Test: `tests/test_service.py`

**Step 1: Write the failing test**

```python
def test_process_pending_schedules_kosis_connection_error():
    # injected verifier raises KosisConnectionError
    # Claim remains PENDING with KOSIS_CONNECTION failure kind
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_service.py::test_process_pending_schedules_kosis_connection_error -q`

**Step 3: Write minimal implementation**

Catch `KosisConnectionError` before the generic exception handler, call `schedule_kosis_retry`, and report `deferred` separately from terminal `failed` counts.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_service.py::test_process_pending_schedules_kosis_connection_error -q`

**Step 5: Commit**

```bash
git add clafact/service/batch.py tests/test_service.py
git commit -m "feat: schedule KOSIS connection retries"
```

### Task 4: Replace traceback display with retry status

**Files:**
- Modify: `streamlit_app.py:86-167,498-505`
- Test: `tests/test_upload_scoped_dashboard.py`

**Step 1: Write the failing test**

```python
def test_dashboard_shows_connection_retry_message_without_error_traceback():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    assert "KOSIS 연결이 지연되고 있습니다" in source
    assert 'st.error(row["error"]' not in source
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_upload_scoped_dashboard.py::test_dashboard_shows_connection_retry_message_without_error_traceback -q`

**Step 3: Write minimal implementation**

- For a Claim with `failure_kind == 'KOSIS_CONNECTION'` and a future retry timestamp, render the connection-delay message and timestamp rather than raw `error` text.
- Keep raw errors available only in the stored record for operators.
- Show `deferred` count in batch feedback.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_upload_scoped_dashboard.py -q && python -m py_compile streamlit_app.py`

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_upload_scoped_dashboard.py
git commit -m "fix: show friendly KOSIS retry status"
```

### Task 5: Full verification and release

**Files:**
- Verify: `tests/test_service.py`, `tests/test_throttle.py`, `tests/test_upload_scoped_dashboard.py`, `tests/test_run.py`, `tests/test_verdict.py`

**Step 1: Run focused regression tests**

Run: `python -m pytest tests/test_service.py tests/test_throttle.py tests/test_upload_scoped_dashboard.py -q`

**Step 2: Run verification modules**

Run: `python -m tests.test_run && python -m tests.test_verdict`

**Step 3: Inspect the final diff**

Run: `git diff --check origin/main..HEAD && git status --short`

**Step 4: Commit plan**

```bash
git add docs/plans/2026-07-25-kosis-transient-retry.md
git commit -m "docs: plan KOSIS transient retry implementation"
```
