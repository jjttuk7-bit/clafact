# KOSIS Candidate Quality Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 인구·고용·무역 수치 문장에 대해 KOSIS 후보를 공통 지표 사전과 공식 항목 신호로 재순위한다.

**Architecture:** `claim_profile.py`는 지표 사전에서 구조화된 주장 프로필을 만든다. `kosis_candidate_search.py`는 그 프로필과 표 제목·공식 항목명을 비교해 100점 환산 후보와 설명 가능한 점수 내역을 만든다. Streamlit은 기존 후보 이력에 결과를 저장·표시한다.

**Tech Stack:** Python 3.11, dataclasses, Streamlit, pytest, 기존 KOSIS 메타데이터 클라이언트.

---

### Task 1: 공통 지표 사전으로 ClaimProfile 확장

**Files:**
- Modify: `clafact/claim_profile.py`
- Test: `tests/test_claim_profile.py`

**Step 1: Write failing tests**

```python
def test_profile_detects_export_value_as_trade_indicator():
    profile = build_claim_profile("7월 수출은 13% 증가했다.")
    assert profile.topic == "무역"
    assert profile.indicator == "수출액"
    assert profile.search_query == "수출액"

def test_profile_distinguishes_employment_rate_from_employed_people():
    assert build_claim_profile("고용률은 62.7%다.").indicator == "고용률"
    assert build_claim_profile("취업자는 2800만명이다.").indicator == "취업자 수"
```

**Step 2: Verify RED**

Run: `python -m pytest tests/test_claim_profile.py -q`

Expected: FAIL because 무역 지표와 동의어가 없다.

**Step 3: Implement minimal registry**

Replace the tuple-only topic matching with immutable indicator specifications containing topic, canonical indicator, aliases, and search query. Preserve existing profile fields and anaphora inheritance.

**Step 4: Verify GREEN**

Run: `python -m pytest tests/test_claim_profile.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/claim_profile.py tests/test_claim_profile.py
git commit -m "feat: extend numeric claim profiles for trade"
```

### Task 2: 단위·공식 항목 기반 후보 재순위

**Files:**
- Modify: `clafact/kosis_candidate_search.py`
- Test: `tests/test_kosis_candidate_search.py`

**Step 1: Write failing tests**

```python
def test_trade_candidate_prefers_export_value_item_over_export_volume_item():
    candidate = evaluate_kosis_candidate(
        "7월 수출은 13% 증가했다.",
        TableHit("DT_EXPORT", "101", "월별 수출입액", "무역통계", 1.0),
        item_names=("수출액 전년동월비(%)", "수출물량지수"),
    )
    assert candidate.selected_item == "수출액 전년동월비(%)"
    assert any("공식 항목 수출액" in item for item in candidate.score_breakdown)
```

**Step 2: Verify RED**

Run: `python -m pytest tests/test_kosis_candidate_search.py::test_trade_candidate_prefers_export_value_item_over_export_volume_item -q`

Expected: FAIL because 공식 항목 선택은 전년 문자열만 본다.

**Step 3: Implement minimal selection and scoring**

Choose the official item with the most matching canonical indicator, unit/comparison tokens, and record positive and negative signals. Keep `fit_score` normalized to 100.

**Step 4: Verify GREEN**

Run: `python -m pytest tests/test_kosis_candidate_search.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/kosis_candidate_search.py tests/test_kosis_candidate_search.py
git commit -m "feat: rank KOSIS candidates by official items"
```

### Task 3: Shadow 후보 기록 검증

**Files:**
- Verify: `streamlit_app.py`
- Verify: `tests/test_kosis_candidate_search.py`
- Verify: `tests/test_kosis_candidate_compat.py`

**Step 1: Run focused tests**

Run: `python -m pytest tests/test_claim_profile.py tests/test_kosis_candidate_search.py tests/test_kosis_candidate_compat.py tests/test_kosis_candidate_run_store.py -q`

Expected: PASS.

**Step 2: Verify Streamlit startup**

Run:

```bash
python -m py_compile streamlit_app.py
python -c "from streamlit.testing.v1 import AppTest; app=AppTest.from_file('streamlit_app.py'); app.run(timeout=60); assert not app.exception; print('Streamlit AppTest: OK')"
```

Expected: `Streamlit AppTest: OK`.

**Step 3: Commit documentation and publish**

```bash
git add docs/plans/2026-07-29-kosis-candidate-quality-*.md
git commit -m "docs: plan KOSIS candidate quality improvements"
```
