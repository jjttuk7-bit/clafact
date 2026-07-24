# KOSIS objL 누락 자동 보완 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |


**Goal:** 필수 objL 분류값을 요구하는 KOSIS 통계표도 오류 20일 때만 안전하게 조회한다.

**Architecture:** `HttpKosisClient.fetch_data()`가 첫 조회의 KOSIS 오류 20을 식별하고, 지정되지 않은 `obj_l2`~`obj_l8`을 하나씩 `ALL`로 보완한다. 실제 요청은 항상 기존 `_call()`을 거쳐 예산·레이트 제한을 적용한다.

**Tech Stack:** Python 3, urllib, pytest.

---

### Task 1: HTTP 재시도 회귀 테스트

**Files:**
- Modify: `tests/test_retrieve_kosis.py`
- Test: `tests/test_retrieve_kosis.py`

**Step 1: Write the failing test**

```python
def test_http_fetch_retries_with_next_objl_after_missing_objl_error():
    # first response is {"err": "20"}, second response is a KOSIS row
    # assert the second request includes objL2=ALL and result is returned
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieve_kosis.py -q`
Expected: FAIL because `fetch_data()` currently raises the first error 20.

### Task 2: 최소 objL 보완 구현

**Files:**
- Modify: `clafact/kosis.py:46-70, 220-229`
- Test: `tests/test_retrieve_kosis.py`

**Step 1: Extend query parameter construction**

```python
for level in range(1, 9):
    query[f"objL{level}"] = params.get(f"obj_l{level}", "ALL" if level == 1 else "")
```

**Step 2: Retry only error 20**

```python
for level in range(2, 9):
    try:
        data = self._call(...)
        break
    except KosisApiError as error:
        if error.code != "20" or f"obj_l{level}" in params:
            raise
        params[f"obj_l{level}"] = "ALL"
```

Use a structured private API error so handling does not parse formatted message strings.

**Step 3: Run targeted tests**

Run: `pytest tests/test_retrieve_kosis.py -q`
Expected: PASS.

### Task 3: Non-20 safety and full regression

**Files:**
- Modify: `tests/test_retrieve_kosis.py`

**Step 1: Add the failing non-20 test**

```python
def test_http_fetch_does_not_retry_non_objl_kosis_error():
    # err 21 should raise after one request
```

**Step 2: Verify focused and full tests**

Run: `pytest tests/test_retrieve_kosis.py tests/test_retrieve.py tests/test_throttle.py -q`
Expected: PASS.

Run: `pytest -q`
Expected: PASS.

### Task 4: Commit

```bash
git add clafact/kosis.py tests/test_retrieve_kosis.py docs/plans/2026-07-24-kosis-objl-fallback-*.md
git commit -m "fix: retry KOSIS requests with required objL levels"
```
