# KOSIS 좌표 선택 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KOSIS 원본 행에서 Claim과 비교할 유일한 좌표를 추천·확인한다.

**Architecture:** 순수 모듈이 API 행을 축·선택값·일치 행으로 변환한다. Streamlit은 기존 조회 스냅샷 컨텍스트를 사용해 선택 UI를 표시하고, 유일 행일 때 기존 근거 입력란을 채운다.

**Tech Stack:** Python, Streamlit, pytest

---

### Task 1: 좌표 추출·필터 순수 함수 테스트

**Files:**
- Create: `tests/test_kosis_coordinate_selection.py`
- Create: `clafact/kosis_coordinate_selection.py`

Write a failing test for extracting `품목·항목·시점·단위` axes, recommending a subject/period/unit, and requiring exactly one matching row.

### Task 2: 좌표 추출·필터 구현

Implement the minimal pure functions and run the focused test.

### Task 3: Streamlit coordinate confirmation UI

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

After snapshot preparation, show `2. 정확한 분류 좌표 선택`, render selectboxes from real API rows, and only prefill evidence fields if one row matches.

### Task 4: Verify and commit

Run `python -m pytest -q` and `python -m py_compile streamlit_app.py`, then commit implementation and tests.
