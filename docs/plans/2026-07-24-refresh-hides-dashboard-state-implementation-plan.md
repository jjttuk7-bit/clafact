# Refresh Hides Dashboard State Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 새로고침 직후 운영 홈의 이전 업로드·누적 통계를 숨기고, 새 CSV 등록 후에만 표시한다.

**Architecture:** `streamlit_app.py`의 Streamlit 세션에 화면 표시 전용 플래그를 둔다. DB 조회·삭제 로직은 변경하지 않으며, 성공한 기사 등록만 플래그를 활성화한다.

**Tech Stack:** Python, Streamlit, pytest

---

### Task 1: Dashboard visibility regression tests

**Files:**
- Modify: `tests/test_upload_scoped_dashboard.py`

**Step 1: Write the failing test**

새로고침 초기 상태에선 운영 통계 카드가 조건부이고, 기사 등록 성공 시 표시 플래그가 켜지며, `새 업로드 시작`이 이를 끄는지 확인하는 소스 회귀 테스트를 추가한다.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`
Expected: 새 표시 플래그가 없어 실패.

### Task 2: Gate dashboard display with session state

**Files:**
- Modify: `streamlit_app.py:300-400`

**Step 1: Implement the minimal code**

`dashboard_initialized`를 기본 `False`로 설정하고, 기사 등록 성공 시 `True`, 새 업로드 시작 시 `False`로 설정한다. 운영 통계 카드 출력은 이 플래그가 참일 때만 수행한다.

**Step 2: Run targeted tests**

Run: `pytest tests/test_upload_scoped_dashboard.py -q`
Expected: PASS.

### Task 3: Verify the change

**Files:**
- Verify: `streamlit_app.py`
- Verify: `tests/test_upload_scoped_dashboard.py`

**Step 1: Compile and run related tests**

Run: `python -m py_compile streamlit_app.py; pytest tests/test_upload_scoped_dashboard.py tests/test_ingest_observability.py tests/test_source_classifier.py tests/test_service.py -q`
Expected: PASS (allowing explicitly skipped tests).

**Step 2: Commit**

```bash
git add streamlit_app.py tests/test_upload_scoped_dashboard.py docs/plans/2026-07-24-refresh-hides-dashboard-state-design.md docs/plans/2026-07-24-refresh-hides-dashboard-state-implementation-plan.md
git commit -m "feat: hide dashboard state after refresh"
```
