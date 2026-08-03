# Atomic Claim 분리 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 품목명·괄호 수치 반복 문장을 독립 Claim으로 분리하고, 각 Claim이 별도 저장·KOSIS 후보 탐색으로 이어지게 한다.

**Architecture:** 순수 파서 `atomic_claim.py`가 원문 문장에서 보수적인 Atomic Claim 목록을 만든다. Claim Card·후보 탐색 저장소는 부모 문장 번호와 Claim 순번으로 식별자를 확장하며, Streamlit은 Atomic Claim 선택지를 화면에 보여 준다. 단일 수치 문장은 `claim_index=1`로 기존 흐름을 유지한다.

**Tech Stack:** Python 표준 라이브러리 `re`, SQLite, Streamlit, pytest.

---

### Task 1: Atomic Claim 파서와 계약 테스트

**Files:** Create `clafact/atomic_claim.py`; test `tests/test_atomic_claim.py`.

1. 먼저 실제 #11 문장을 넣어 배추·무·쌀의 `(순번, 품목, 원문값, 단위)`가 보존되는 실패 테스트를 작성한다.
2. `python -m pytest tests/test_atomic_claim.py -q`를 실행해 모듈 미존재로 실패하는 것을 확인한다.
3. 불변 `AtomicClaim` 자료형과 `extract_atomic_claims()`를 최소 구현한다. 명시 단위가 있는 `품목명(수치)`가 두 개 이상일 때만 결과를 낸다.
4. 같은 테스트를 통과시킨다.
5. `feat: extract conservative atomic Claims`로 커밋한다.

### Task 2: Claim Card 저장소를 Claim 순번으로 확장

**Files:** Modify `clafact/claim_card_store.py`; test `tests/test_claim_card_store.py`.

1. 부모 문장 #11 아래 claim_index 1과 2의 서로 다른 Claim Card가 공존하는 실패 테스트를 작성한다.
2. 테스트가 현재의 `(shadow_run_id, row_index)` 기본키 충돌로 실패하는 것을 확인한다.
3. 새 테이블은 `(shadow_run_id, row_index, claim_index)` 기본키를 쓰고, 기존 DB에는 `claim_index=1`을 추가하는 이관을 구현한다. 공개 메서드의 기본값은 1로 둔다.
4. focused test를 통과시킨다.
5. `feat: store Claim Cards by atomic claim index`로 커밋한다.

### Task 3: 후보 탐색 이력의 Claim 순번 연결

**Files:** Modify `clafact/kosis_candidate_run_store.py`; test `tests/test_kosis_candidate_run_store.py`.

1. 같은 문장 #11의 claim_index 1·2 검색 이력이 분리되는 실패 테스트를 쓴다.
2. 실패를 확인한다.
3. 저장소와 CSV 출력에 `claim_index`를 기본값 1로 추가하고, 기존 이력과 호환시킨다.
4. focused test를 통과시킨다.
5. `feat: trace candidate searches by atomic claim`으로 커밋한다.

### Task 4: Streamlit의 Atomic Claim 선택·저장·탐색 연결

**Files:** Modify `streamlit_app.py`; test `tests/test_streamlit_shadow_guide_safety.py`.

1. `extract_atomic_claims`, `claim_index`, `Atomic Claim` 선택 UI 존재를 검사하는 실패 source-contract test를 쓴다.
2. 실패를 확인한다.
3. 선택 문장에서 Atomic Claim을 찾고, 둘 이상이면 `#11-1 · 배추 · -34.5%` 형식의 `검증할 Atomic Claim` 선택기를 표시한다.
4. 선택한 Claim의 값으로 Claim Card를 만들고, ClaimCardStore·세션 키·후보 탐색 이력에 claim_index를 전달한다. subject는 모집단으로 오인하지 않고 후속 좌표 단계용 품목 정보로만 표시한다.
5. Atomic Claim이 없으면 기존의 단일 Claim 흐름을 claim_index=1로 그대로 유지한다.
6. focused test를 통과시킨다.
7. `feat: select atomic Claims in Shadow workflow`로 커밋한다.

### Task 5: 전체 검증·이슈대장·병합

1. `python -m pytest -q` 전체 회귀 테스트를 실행한다.
2. `git diff main...HEAD --check`로 diff 오류가 없는지 확인한다.
3. 사용자용 이슈대장의 ISS-002를 `검증 중`으로 바꾸고, 구현 커밋·자동 테스트·Cloud 확인 조건을 기록한다.
4. `main`에 fast-forward 병합 후 `origin/main`으로 push한다.
