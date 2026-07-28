# KOSIS 후보 탐색 실행 이력 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow의 KOSIS 후보 탐색 결과를 연구 전용 DB에 누적하고 CSV로 내보낸다.

**Architecture:** 후보 탐색 실행과 후보 행을 SQLite에 저장한다. 화면은 검색 성공 직후 저장하고, 최근 실행을 표·CSV로 제공한다. 운영 데이터는 수정하지 않는다.

**Tech Stack:** Python, SQLite, pytest, Streamlit.

---

### Task 1: 저장소 테스트와 구현

**Files:**
- Create: `clafact/kosis_candidate_run_store.py`
- Create: `tests/test_kosis_candidate_run_store.py`

**Step 1:** 후보 3개 실행을 저장·조회·CSV 행으로 펼치는 실패 테스트를 작성한다.

**Step 2:** `pytest tests/test_kosis_candidate_run_store.py -q`로 실패를 확인한다.

**Step 3:** SQLite 저장소와 append/list/export 행 생성을 최소 구현한다.

**Step 4:** 같은 테스트를 재실행해 통과를 확인한다.

### Task 2: Shadow 화면 연결

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_kosis_candidate_run_store.py`

**Step 1:** 후보 검색 직후 실행 ID·문장·검색어·후보를 저장한다.

**Step 2:** 최근 후보 탐색 이력과 CSV 다운로드를 표시한다.

**Step 3:** 후보·매핑·CSV 관련 회귀 테스트와 Streamlit AppTest를 실행한다.
