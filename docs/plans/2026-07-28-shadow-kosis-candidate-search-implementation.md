# Shadow KOSIS 자동 후보 탐색 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow 문장에 대해 설명 가능한 KOSIS 통계표 후보 상위 3개를 제시한다.

**Architecture:** 기존 `KosisSearchIndex`와 KOSIS 통합검색을 사용해 표 후보를 얻고, 새 순수 후보 평가기가 문장과 표 제목을 규칙 기반으로 점수화한다. Streamlit Shadow 화면은 검색·점수·사유를 보여 주되, 기존 근거 객체와 매핑의 승인 흐름은 바꾸지 않는다.

**Tech Stack:** Python, pytest, Streamlit, KOSIS Open API.

---

### Task 1: 후보 평가기 테스트와 구현

**Files:**
- Create: `clafact/kosis_candidate_search.py`
- Create: `tests/test_kosis_candidate_search.py`

**Step 1: Write the failing tests**

`소비자물가가 지난해 같은 달 대비 2.4% 상승` 문장에 대해 월별·등락률 표가 연도별 지수 표보다 높은 점수를 받고, 각 사유를 반환하는 테스트를 작성한다.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_kosis_candidate_search.py -q`

Expected: 모듈 또는 평가 함수가 없어 FAIL.

**Step 3: Write minimal implementation**

후보 dataclass와 지표·월/분기/연·퍼센트·전년동월비 표현을 평가하는 순수 함수를 구현한다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_kosis_candidate_search.py -q`

Expected: PASS.

### Task 2: KOSIS 검색 결과 결합 테스트와 구현

**Files:**
- Modify: `clafact/kosis_candidate_search.py`
- Modify: `tests/test_kosis_candidate_search.py`

**Step 1: Write the failing test**

가짜 검색 인덱스의 `TableHit` 목록을 받아 점수 순 상위 3개 후보로 반환하는 테스트를 작성한다.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_kosis_candidate_search.py -q`

Expected: 검색 결합 함수가 없어 FAIL.

**Step 3: Write minimal implementation**

검색 인덱스 호출, 후보 평가, 안정적인 점수·검색순위 정렬, 상위 3개 제한을 구현한다. 검색 오류는 호출자에게 설명 가능한 오류로 전달한다.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_kosis_candidate_search.py -q`

Expected: PASS.

### Task 3: Shadow 화면 표시와 회귀 검증

**Files:**
- Modify: `streamlit_app.py`
- Test: `tests/test_kosis_candidate_search.py`

**Step 1: Write the failing test**

후보가 없을 때·API 키가 없을 때에도 수동 근거 입력 흐름이 유지되는지 검증한다.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_kosis_candidate_search.py -q`

Expected: UI 보조 함수 또는 오류 경계가 없어 FAIL.

**Step 3: Write minimal implementation**

`KOSIS 후보 탐색` expander에 Shadow 문장 선택, 후보 탐색 버튼, 제목·기관·점수·사유·KOSIS URL을 표시한다. 결과는 session state에만 보관하고 운영 데이터는 수정하지 않는다.

**Step 4: Run focused regression tests**

Run: `pytest tests/test_kosis_candidate_search.py tests/test_shadow_export.py tests/test_kosis_shadow_mapping_store.py -q`

Expected: PASS.

**Step 5: Commit**

```powershell
git add clafact/kosis_candidate_search.py streamlit_app.py tests/test_kosis_candidate_search.py docs/plans/2026-07-28-shadow-kosis-candidate-search-design.md docs/plans/2026-07-28-shadow-kosis-candidate-search-implementation.md
git commit -m "feat: suggest KOSIS candidates in shadow mode"
```
