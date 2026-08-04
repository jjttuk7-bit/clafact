# Claim Candidate Retrieval Improvement Implementation Plan

> **For Codex:** Implement task-by-task with test-first verification.

**Goal:** Improve real KOSIS Top-3 retrieval for the Goldset failure cases by preserving specific Claim terms in the search query and candidate ranking.

**Architecture:** Extend `ClaimProfile` with a reviewable `qualifiers` field. Build a KOSIS query from the canonical indicator plus detected qualifier, then apply a transparent qualifier match weight to candidate title, survey, and official items. The change does not choose the final table automatically.

**Tech Stack:** Python 3.11+, pytest, KOSIS OpenAPI client, Streamlit consumer.

---

### Task 1: Define failing Claim-profile cases

**Files:**
- Modify: `tests/test_claim_profile.py`
- Modify: `clafact/claim_profile.py`

1. Add failing tests that expect `배추` to remain a qualifier for a consumer-price Claim and `사망자 수` to become a supported population indicator.
2. Run the focused tests and confirm they fail because the fields and aliases are absent.
3. Add the minimum immutable `qualifiers` field and relevant alias specifications.
4. Re-run the focused tests and confirm they pass.

### Task 2: Define failing retrieval and reranking cases

**Files:**
- Modify: `tests/test_kosis_candidate_search.py`
- Modify: `clafact/kosis_candidate_search.py`

1. Add a failing test that asserts a `배추` Claim sends `배추 소비자물가` to the KOSIS search index.
2. Add a failing test that a table containing `배추` outranks a generic consumer-price table for the same Claim.
3. Run the focused tests and confirm both fail for missing qualifier-aware behavior.
4. Add a query builder and a transparent qualifier score, retaining the zero-query safety rule.
5. Re-run focused and existing candidate-search tests.

### Task 3: Add Goldset-derived regression cases

**Files:**
- Modify: `tests/test_claim_profile.py`
- Modify: `tests/test_kosis_candidate_search.py`

1. Add tests for economic-activity population and vital-statistics aliases selected from the real failure log.
2. Confirm new tests fail before their corresponding alias/ranking behavior exists.
3. Implement only the specifications needed to make the cases pass.
4. Run `pytest tests/test_claim_profile.py tests/test_kosis_candidate_search.py -q`.

### Task 4: Measure actual KOSIS impact

**Files:**
- Create: `ClaFact_완성형_핵심작업기록/05_2026-08-04_오늘작업_문서와_결과물/ClaFact_Shadow_후보탐색_실측평가_v2_골든셋20건.xlsx`

1. Load `.env` in process only; never print or store the API key.
2. Execute the same 20 Goldset Claims sequentially through `HttpKosisClient → KosisSearchIndex → suggest_kosis_candidates`.
3. Compare results to the v1 measurement and record Top-1, Recall@3, MRR, failures, and exclusions.
4. Keep failures that remain after expansion visible.

### Task 5: Full verification and integration

**Files:**
- Verify: `tests/test_claim_profile.py`
- Verify: `tests/test_kosis_candidate_search.py`
- Verify: the actual evaluation workbook

1. Run all relevant tests freshly.
2. Inspect the changed-file diff and confirm no unrelated dirty files are included.
3. Commit only the code, tests, plans, and evaluation artifact created by this goal.
4. Push only after the user requests it.
