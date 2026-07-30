# KOSIS 스냅샷 조회 시간 제한 하드닝 구현 계획

| 항목 | 내용 |
|---|---|
| Author | ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-30 |

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KOSIS 후보 보강과 스냅샷 준비가 제한된 UI 조회 예산 안에서 실패 원인을 보존하며 종료되게 한다.

**Architecture:** `HttpKosisClient`에 UI 전용 요청 제한(요청 시간, 연결 재시도, `objL` 보완 횟수)을 전달할 수 있게 한다. Streamlit은 이 제한된 클라이언트를 후보 보강과 스냅샷 준비에 공통 사용하고, 제한 초과·연결 실패·표 파라미터 실패를 구분해 재시도 가능한 메시지로 표시한다.

**Tech Stack:** Python, Streamlit, urllib, pytest

---

### Task 1: 제한된 KOSIS 조회 계약을 테스트로 정의

**Files:**
- Modify: `tests/test_retrieve_kosis.py`
- Modify: `tests/test_kosis_candidate_search.py`

**Step 1: 실패 테스트 작성**

- `HttpKosisClient`가 UI 제한에서 `objL` 보완 요청 수를 넘기지 않는 테스트를 추가한다.
- 후보 메타데이터 조회가 실패해도 후보 정렬 결과가 유지되는 테스트를 추가한다.

**Step 2: RED 확인**

Run: `pytest tests/test_retrieve_kosis.py tests/test_kosis_candidate_search.py -q`

Expected: 새 제한 계약 테스트가 실패한다.

### Task 2: HTTP 클라이언트에 제한 옵션 추가

**Files:**
- Modify: `clafact/kosis.py`
- Test: `tests/test_retrieve_kosis.py`

**Step 1: 최소 구현**

- 기본 동작을 보존한 채 요청 시간, 연결 재시도 횟수, `objL` 보완 횟수를 생성자 옵션으로 받는다.
- 제한 초과 시 표 식별자와 재시도·보완 횟수가 포함된 예외를 발생시킨다.

**Step 2: GREEN 확인**

Run: `pytest tests/test_retrieve_kosis.py -q`

Expected: 기존 재시도·예산 테스트와 새 제한 테스트가 통과한다.

### Task 3: Streamlit UI에 제한 프로필과 오류 메시지 연결

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_light_surfaces.py` 또는 새 UI 계약 테스트

**Step 1: 실패 테스트 작성**

- 후보 탐색과 스냅샷 준비가 동일한 UI 제한 프로필을 사용하고, 실패 시 재시도 안내를 렌더링하는 계약을 추가한다.

**Step 2: 최소 구현**

- `load_engine()`과 스냅샷 준비에서 같은 제한 클라이언트를 사용한다.
- 연결 지연·표 파라미터 보완 제한·호출 예산 오류를 구분해 표시한다.
- 성공한 스냅샷만 현재의 근거 저장 흐름으로 전달한다.

**Step 3: GREEN 확인**

Run: `pytest tests/test_streamlit_light_surfaces.py tests/test_kosis_candidate_search.py -q`

Expected: UI 계약과 후보 회복성 테스트가 통과한다.

### Task 4: 회귀 검증과 수동 점검

**Files:**
- Verify: `tests/test_retrieve_kosis.py`
- Verify: `tests/test_kosis_candidate_search.py`
- Verify: `tests/test_kosis_snapshot_preparation.py`
- Verify: `tests/test_kosis_value_comparison_card.py`

**Step 1: 전체 관련 테스트 실행**

Run: `pytest tests/test_retrieve_kosis.py tests/test_kosis_candidate_search.py tests/test_kosis_snapshot_preparation.py tests/test_kosis_value_comparison_card.py -q`

**Step 2: 변경 형식 검사**

Run: `git diff --check`

**Step 3: 수동 점검**

- KOSIS 후보 탐색에서 지연 표가 있더라도 화면이 제한된 시간 안에 반환되는지 확인한다.
- 실패 안내 뒤 재시도 버튼으로 같은 흐름을 다시 시작할 수 있는지 확인한다.

**Step 4: 커밋**

Run: `git add clafact/kosis.py streamlit_app.py tests/ && git commit -m "fix: bound KOSIS snapshot preparation"`
