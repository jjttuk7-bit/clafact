# Shadow Semantic Card Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow Mode에서 후보 KOSIS 표를 확인 가능한 7축 Semantic Card로 저장·재사용하고, Claim의 지역·모집단을 독립 축으로 매칭·표시한다.

**Architecture:** `ClaimProfile`에 지역·모집단을 추가하고 후보 점수에 별도 신호를 추가한다. 실행 이력과 별개인 SQLite 기반 `KosisSemanticCardStore`를 신설해, 사람 확인을 마친 후보 Card만 영속화한다. Streamlit은 후보 Card 초안의 7축을 표시하고, 저장·재사용·상태 집계를 기존 Evidence 단계 앞에 연결한다.

**Tech Stack:** Python 3, pytest, SQLite, Streamlit, KOSIS OpenAPI.

---

### Task 1: Claim 지역·모집단 추출

**Files:**
- Modify: `clafact/claim_profile.py`
- Modify: `tests/test_claim_profile.py`

**Step 1: Write the failing test**

```python
def test_extracts_region_and_population_as_independent_claim_axes():
    profile = build_claim_profile("2025년 3월 서울 청년층 실업률은 7.5%였다.")
    assert profile.region == "서울"
    assert profile.population == "청년층"
    assert "지역=서울" in profile_summary(profile)
    assert "모집단=청년층" in profile_summary(profile)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_claim_profile.py::test_extracts_region_and_population_as_independent_claim_axes -v`

Expected: FAIL because `region` and `population` do not yet exist.

**Step 3: Write minimal implementation**

Add `region` and `population` fields to `ClaimProfile`; add explicit Korean region and common population patterns; preserve inherited profile values only when the current sentence has no explicit value.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_claim_profile.py -v`

Expected: PASS.

### Task 2: Candidate scoring for independent axes

**Files:**
- Modify: `clafact/kosis_candidate_search.py`
- Modify: `tests/test_kosis_candidate_search.py`

**Step 1: Write the failing test**

Create two same-indicator candidate tables: one with `서울·청년` terms and one with incompatible `전국·전체` terms. Assert that the score breakdown contains distinct region and population signals and ranks the compatible table first.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_kosis_candidate_search.py -k "region or population" -v`

Expected: FAIL because the separate score signals do not exist.

**Step 3: Write minimal implementation**

Add explainable region and population match/penalty helpers based on table title, survey and available official item names. Do not discard candidates merely because metadata is incomplete.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_kosis_candidate_search.py tests/test_claim_profile.py -v`

Expected: PASS.

### Task 3: Semantic Card model, draft builder and persistent Store

**Files:**
- Create: `clafact/kosis_semantic_card.py`
- Create: `clafact/kosis_semantic_card_store.py`
- Create: `tests/test_kosis_semantic_card.py`
- Create: `tests/test_kosis_semantic_card_store.py`

**Step 1: Write failing tests**

Test that a candidate and Claim Profile produce a draft with all seven axes; test that a confirmed Card persists, is read by `table_id`, updates safely, and an unconfirmed draft is not persisted.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_kosis_semantic_card.py tests/test_kosis_semantic_card_store.py -v`

Expected: FAIL because these modules do not exist.

**Step 3: Write minimal implementation**

Implement:

```python
SemanticCardDraft(table_id, org_id, table_name, topic, indicator,
                  target_scope, spatial, time, unit, definition_formula,
                  field_status, source, confidence)
```

Use SQLite keyed by `table_id`; store JSON values and confirmation timestamp. Build drafts from the candidate hit, Claim Profile, selected item and the existing candidate score evidence. Use `confirmed` as the only state admitted to the reusable Catalog.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_kosis_semantic_card.py tests/test_kosis_semantic_card_store.py -v`

Expected: PASS.

### Task 4: Candidate Card reuse and summary helpers

**Files:**
- Modify: `clafact/shadow_ui.py`
- Modify: `tests/test_shadow_ui.py`

**Step 1: Write failing tests**

Test a summary that reports total confirmed Cards, current-run new Cards, current-run reused Cards and pending candidates. Test that stored Card values override matching draft fields while keeping the current candidate score explanation.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shadow_ui.py -k "semantic_card" -v`

Expected: FAIL because Card summary helpers do not exist.

**Step 3: Write minimal implementation**

Add pure display helpers only; do not put database logic in `shadow_ui.py`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shadow_ui.py -v`

Expected: PASS.

### Task 5: Streamlit Semantic Card confirmation flow

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_app.py` or the existing focused UI helper tests

**Step 1: Write failing test**

Add a focused test for the pure Card-draft/view-model helper used by the page: it must expose all seven axes, field states, and independent Claim `region`/`population` values.

**Step 2: Run test to verify it fails**

Run: `pytest <focused-test-path> -v`

Expected: FAIL because the view model does not yet exist.

**Step 3: Write minimal implementation**

At `KOSIS 후보 탐색`:

1. Build a draft for each result.
2. Load existing confirmed Cards by `table_id` and mark them `재사용`.
3. Show each 7-axis Card with Claim comparison and score/penalty reasons.
4. Provide editable review fields and a `Semantic Card 확인·저장` action.
5. On confirmation, persist the Card and prefill the existing Evidence flow.
6. Add the four Catalog metrics to `현재 구현된 Semantic 검증 상태`.

Do not auto-save search results; do not change existing Snapshot and Claim completion behaviour.

**Step 4: Run focused tests**

Run: `pytest tests/test_claim_profile.py tests/test_kosis_candidate_search.py tests/test_kosis_semantic_card.py tests/test_kosis_semantic_card_store.py tests/test_shadow_ui.py -v`

Expected: PASS.

### Task 6: Regression verification and documentation

**Files:**
- Modify: `docs/plans/2026-08-03-shadow-semantic-card-design.md` only if implementation details differ

**Step 1: Run full relevant tests**

Run: `pytest tests/test_claim_profile.py tests/test_kosis_candidate_search.py tests/test_retrieve_kosis.py tests/test_kosis_candidate_run_store.py tests/test_shadow_ui.py tests/test_kosis_semantic_card.py tests/test_kosis_semantic_card_store.py -v`

Expected: PASS.

**Step 2: Run static syntax check**

Run: `python -m py_compile streamlit_app.py clafact/claim_profile.py clafact/kosis_candidate_search.py clafact/kosis_semantic_card.py clafact/kosis_semantic_card_store.py`

Expected: exit 0.

**Step 3: Review changes**

Run: `git diff --check; git diff -- streamlit_app.py clafact tests docs/plans`

Expected: no whitespace errors; only intended feature files changed.

**Step 4: Commit**

```bash
git add streamlit_app.py clafact tests docs/plans
git commit -m "feat: add reusable KOSIS semantic cards"
```
