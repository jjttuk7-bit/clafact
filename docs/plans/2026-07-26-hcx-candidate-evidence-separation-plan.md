# HCX 후보 탐지·근거 충분성 분리 Implementation Plan

> **For Codex:** Implement task-by-task with test-first verification.

**Goal:** HCX가 검증 후보 여부와 기사 내부 근거 충분성을 별도 결과로 반환·표시하도록 만든다.

**Architecture:** `detect_llm.py`에 구조화된 HCX 판정 결과를 도입하고, 기존 `judge` 호환 API는 후보 불리언과 통합 사유를 반환한다. 실험실의 독립 모드 결과는 근거 상태와 원문 인용 구간을 유지해 표기한다.

**Tech Stack:** Python 3, dataclasses, JSON, pytest, Streamlit.

---

### Task 1: HCX 응답 계약 테스트

**Files:**
- Modify: `tests/test_experiment_lab.py`
- Modify: `tests/test_hcx_contract.py`
- Modify: `clafact/pipeline/detect_llm.py`

1. 2번 문장의 기대 결과 `candidate=true`, `evidence_status=needs_retrieval` 테스트를 작성한다.
2. 테스트가 기존 불리언 API에서 실패하는지 실행한다.
3. 구조화된 판정 결과와 JSON 파서를 최소 구현한다.
4. 대상 테스트를 다시 실행한다.

### Task 2: 실험실 결과 전달

**Files:**
- Modify: `clafact/experiment_modes.py`
- Modify: `clafact/experiment_lab.py`
- Modify: `tests/test_experiment_lab.py`

1. `ModeRow`에 근거 상태·근거 사유·원문 인용 구간을 추가하는 실패 테스트를 작성한다.
2. HCX 모드와 하이브리드 모드가 구조화된 결과를 보존하도록 구현한다.
3. 기존 tuple judge 의존 테스트를 유지한다.

### Task 3: UI 근거 분리

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_experiment_lab_ui.py`

1. `근거 상태: 검색 필요`과 `HCX 후보 판정: 탐지`가 동시에 표시되는 UI 계약 테스트를 작성한다.
2. 상세 화면과 비교표에 별도 열/줄을 추가한다.
3. Streamlit UI 계약 테스트를 실행한다.

### Task 4: 문제 원장 갱신 및 전체 검증

**Files:**
- Modify: `docs/VERIFICATION_LAB_ISSUE_LEDGER.md`

1. VLAB-009에 실제 원인, 변경 커밋, 통과 테스트를 기록한다.
2. 실험실 관련 전체 테스트와 `py_compile`, `git diff --check`를 실행한다.
3. VLAB-009 상태를 `Resolved` 또는 남은 사항에 맞는 상태로 갱신한다.
