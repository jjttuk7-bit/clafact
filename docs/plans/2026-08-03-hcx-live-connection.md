# HCX Live Connection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow Mode가 `.env`의 HCX 키를 읽어 실제 HCX 판정을 실행하고, 실행 상태를 명확히 표시한다.

**Architecture:** 시작 시 프로젝트 루트 `.env`를 한 번 로드하고, HCX 실행 가능 여부를 단일 함수로 판정한다. 키가 있고 명시적으로 fixture 모드를 고르지 않은 경우 live를 사용하며, UI는 현재 모드와 차단 사유를 표시한다.

**Tech Stack:** Python, Streamlit, python-dotenv, pytest, NCP CLOVA Studio HCX v3.

---

### Task 1: HCX 설정 판정 회귀 테스트

**Files:**
- Create: `tests/test_hcx_runtime_config.py`
- Modify: `clafact/llm.py`

**Step 1:** `.env` 키와 모드 값에 따른 live/fixture 판정을 검증하는 실패 테스트를 작성한다.

**Step 2:** 테스트가 현재 설정 해석 함수 부재로 실패함을 확인한다.

**Step 3:** `.env` 로딩과 HCX 상태 판정 함수를 최소 구현한다.

**Step 4:** 테스트를 다시 실행해 통과를 확인한다.

### Task 2: Shadow Mode 연결

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_experiment_lab_ui.py`

**Step 1:** live 설정이 있을 때 상태가 표시되는 UI 요구 테스트를 작성한다.

**Step 2:** 테스트가 실패함을 확인한다.

**Step 3:** 기존의 분산된 환경변수 조건을 공통 설정 함수로 교체하고, 상태 안내를 표시한다.

**Step 4:** UI 테스트를 통과시킨다.

### Task 3: 검증 및 배포

**Files:**
- Test: `tests/test_hcx_runtime_config.py`, `tests/test_experiment_lab_ui.py`, `tests/test_hcx_contract.py`

**Step 1:** HCX 설정·UI·계약 테스트를 실행한다.

**Step 2:** 실제 키가 설정된 환경에서 HCX 단건 smoke 호출을 한 번만 실행한다.

**Step 3:** 변경 파일만 커밋하고 `main`에 반영한 뒤 푸시한다.
