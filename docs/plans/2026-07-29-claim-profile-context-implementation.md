# Claim Profile Context Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow Mode의 수치 문장을 범용 ClaimProfile로 구조화하고 문맥을 보완해 KOSIS 후보 탐색을 물가·고용·인구에 확장한다.

**Architecture:** `clafact/claim_profile.py`가 규칙 기반의 재현 가능한 문장 해석을 담당한다. 후보 탐색은 ClaimProfile의 검색어와 신호만 사용하며, Streamlit은 프로필·문맥 출처·후보 부족 상태를 연구 기록으로 보여 준다.

**Tech Stack:** Python 3, dataclasses, pytest, Streamlit.

---

### Task 1: 범용 ClaimProfile 모델과 문장 해석

**Files:**
- Create: `clafact/claim_profile.py`
- Create: `tests/test_claim_profile.py`

**Step 1: Write the failing test**

```python
def test_extracts_population_profile_from_numeric_claim():
    profile = build_claim_profile("지난해 출생아 수는 23만 명으로 전년보다 감소했다.")
    assert profile.topic == "인구"
    assert profile.indicator == "출생아 수"
    assert profile.unit == "명"
    assert profile.search_query == "출생아 수"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_claim_profile.py::test_extracts_population_profile_from_numeric_claim -q`

**Step 3: Write minimal implementation**

Define an immutable `ClaimProfile` and explicit topic/indicator/period/unit/comparison token maps. Generate the search query from the most specific detected indicator.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_claim_profile.py -q`

**Step 5: Commit**

```bash
git add clafact/claim_profile.py tests/test_claim_profile.py
git commit -m "feat: extract structured numeric claim profiles"
```

### Task 2: 앞 문장 문맥 보완

**Files:**
- Modify: `clafact/claim_profile.py`
- Modify: `tests/test_claim_profile.py`

**Step 1: Write the failing test**

```python
def test_inherits_indicator_for_anaphoric_followup_sentence():
    previous = build_claim_profile("10월 소비자물가가 2.4% 상승했다.")
    profile = build_claim_profile("이같은 물가 상승률은 15개월 만에 가장 높다.", previous=previous)
    assert profile.indicator == "소비자물가"
    assert profile.context_inherited is True
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_claim_profile.py::test_inherits_indicator_for_anaphoric_followup_sentence -q`

**Step 3: Write minimal implementation**

Only inherit topic and indicator when an anaphoric token is present and the current sentence has no specific indicator. Preserve the current sentence's period, unit, and values.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_claim_profile.py -q`

**Step 5: Commit**

```bash
git add clafact/claim_profile.py tests/test_claim_profile.py
git commit -m "feat: inherit numeric claim context"
```

### Task 3: 프로필 기반 KOSIS 후보 탐색과 후보 부족 상태

**Files:**
- Modify: `clafact/kosis_candidate_search.py`
- Modify: `tests/test_kosis_candidate_search.py`

**Step 1: Write the failing test**

```python
def test_search_uses_profile_query_for_employment_claim():
    candidates = suggest_kosis_candidates("지난해 고용률은 62%였다.", FakeIndex())
    assert fake_index.last_query == "고용률"

def test_returns_no_candidates_when_profile_has_no_supported_indicator():
    assert suggest_kosis_candidates("경제가 어렵다.", FakeIndex()) == []
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_kosis_candidate_search.py -q`

**Step 3: Write minimal implementation**

Build a profile before search, use its query, and return an explicit empty result for unsupported/no-indicator claims. Keep raw ranking internally and 100-point fit display externally.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_kosis_candidate_search.py -q`

**Step 5: Commit**

```bash
git add clafact/kosis_candidate_search.py tests/test_kosis_candidate_search.py
git commit -m "feat: search KOSIS from numeric claim profiles"
```

### Task 4: Shadow Mode 프로필·후보 부족 표시

**Files:**
- Modify: `streamlit_app.py`
- Test: Streamlit AppTest

**Step 1: Write the failing test**

Add a focused AppTest assertion for the profile caption and no-candidate notice.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_shadow_mode.py -q`

**Step 3: Write minimal implementation**

Show the extracted topic, indicator, period, comparison, unit, and “앞 문장 문맥 보완” marker above candidate results. If no supported indicator exists, show “KOSIS 후보 부족 — 수동 근거 입력 또는 보류 검토 필요” rather than zero-score tables.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_streamlit_shadow_mode.py -q`

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_shadow_mode.py
git commit -m "feat: show Shadow claim profiles and candidate gaps"
```

### Task 5: 통합 검증과 배포

**Files:**
- Verify only

**Step 1: Run focused tests**

Run: `python -m pytest tests/test_claim_profile.py tests/test_kosis_candidate_search.py tests/test_kosis_evidence.py tests/test_kosis_evidence_store.py tests/test_kosis_shadow_mapping.py tests/test_kosis_shadow_mapping_store.py tests/test_shadow_export.py -q`

**Step 2: Verify app startup**

Run: `python -m py_compile streamlit_app.py`

Run: `python -c "from streamlit.testing.v1 import AppTest; app=AppTest.from_file('streamlit_app.py'); app.run(timeout=60); assert not app.exception; print('Streamlit AppTest: OK')"`

**Step 3: Commit and push**

```bash
git add docs/plans
git commit -m "docs: plan generic numeric claim profiling"
git push origin feature/kosis-evidence-object
git -C C:\\Users\\USER\\Desktop\\클라비_아이펠톤\\clafact merge --ff-only feature/kosis-evidence-object
git -C C:\\Users\\USER\\Desktop\\클라비_아이펠톤\\clafact push origin main
```
