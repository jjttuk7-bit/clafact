# Review Queue and Batch Verification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 저장된 위험 Claim을 검증자 리뷰에 표시하고, 현재 페이지의 대기 Claim 최대 50건을 독립적으로 일괄 검증한다.

**Architecture:** `Store.review_queue()`를 리뷰 탭에서 사용하고, 검증 탭은 현재 페이지의 PENDING claim_id만 `process_pending`에 전달한다. 개별 실패는 격리하며 불일치·판단불가·저신뢰 결과는 리뷰 큐에 보존한다.

**Tech Stack:** Streamlit, SQLite, Python, pytest.

---

### Task 1: Stored review queue
- Test `tests/test_upload_scoped_dashboard.py` for `review_queue()` rendering.
- Implement saved Claim list and approve/hold/reject actions in `streamlit_app.py`.

### Task 2: Page batch verification
- Test `tests/test_upload_scoped_dashboard.py` for a “현재 페이지 50건 검증” action.
- Send at most current page PENDING claim IDs to `process_pending`; render result counts and rerun.

### Task 3: Verification
- Run dashboard, service, and batch tests; compile Streamlit; commit only changed files.