# KOSIS 재검증 피드백 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-24 |


**Goal:** 재검증 버튼의 실행 상태와 결과를 사용자에게 명확히 보여 준다.

**Architecture:** `render_stored_claim()`의 실패 분기는 `process_pending()` 반환 통계를 세션 상태에 저장하고 재실행한다. 검증 화면의 시작 부분이 그 메시지를 소비해 표시하며, `audit.code_version()`으로 코드 버전도 제공한다.

**Tech Stack:** Python, Streamlit, pytest.

---

### Task 1: 실패하는 UI 계약 테스트

**Files:**
- Modify: `tests/test_upload_scoped_dashboard.py`
- Test: `tests/test_upload_scoped_dashboard.py`

1. 재검증 분기에 `st.spinner`, 세션 상태 결과, `stats['processed']`, `stats['failed']`가 있다는 테스트를 작성한다.
2. `pytest tests/test_upload_scoped_dashboard.py -q`를 실행해 실패를 확인한다.

### Task 2: 최소 UI 피드백 구현

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_upload_scoped_dashboard.py`

1. 재검증 호출을 `st.spinner`로 감싼다.
2. 반환 통계와 코드 버전을 `st.session_state['retry_feedback']`에 기록한다.
3. 검증 화면이 해당 메시지를 한 번 표시·소비하고 실행 코드 버전을 보여 준다.
4. 대상 테스트를 재실행해 통과를 확인한다.

### Task 3: 회귀 검증과 커밋

Run: `python -m py_compile streamlit_app.py`

Run: `pytest tests/test_upload_scoped_dashboard.py tests/test_service.py -q`

Commit: `git commit -m "fix: show KOSIS retry feedback"`
