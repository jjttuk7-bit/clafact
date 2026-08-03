# Claim Card Standardization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make one selected Shadow candidate sentence into a reviewed, persisted Claim Card that is the only permitted input for KOSIS candidate discovery.

**Architecture:** `claim_card.py` composes the existing rule parser, profile extractor, and source classifier into a serializable Claim Card. A small SQLite store persists only confirmed cards by Shadow run and sentence row. The Shadow UI places the confirmation step immediately before KOSIS search and forwards the confirmed profile to the existing ranking engine.

**Tech Stack:** Python 3.11+, dataclasses, SQLite, Streamlit, pytest.

---

### Task 1: Define the Claim Card domain object

**Files:**
- Create: `clafact/claim_card.py`
- Test: `tests/test_claim_card.py`

**Step 1: Write the failing test**

```python
def test_build_claim_card_combines_profile_parse_and_source_fields():
    card = build_claim_card("2025년 3월 서울 청년층 실업률은 7.5%였다.", "2025-04-01")
    assert card.indicator == "실업률"
    assert card.period == "2025-03"
    assert card.claim_value_raw == "7.5%"
    assert card.ready_for_kosis is True
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_claim_card.py -v`

Expected: FAIL because `clafact.claim_card` does not exist.

**Step 3: Write minimal implementation**

Create an immutable `ClaimCard`, `build_claim_card`, conversion back to `ClaimProfile`, and readiness reasons. Use parser output for actual time/value and existing profile/classifier output for semantic fields.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_claim_card.py -v`

Expected: PASS.

### Task 2: Persist only confirmed Claim Cards

**Files:**
- Create: `clafact/claim_card_store.py`
- Create: `tests/test_claim_card_store.py`

**Step 1: Write the failing test**

```python
def test_store_reuses_confirmed_card_for_same_shadow_row(tmp_path):
    with ClaimCardStore(tmp_path / "cards.db") as store:
        assert store.upsert("run-1", 4, confirmed_card) is True
        assert store.get("run-1", 4)["indicator"] == "실업률"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_claim_card_store.py -v`

Expected: FAIL because the store does not exist.

**Step 3: Write minimal implementation**

Use SQLite with `(shadow_run_id, row_index)` as primary key, JSON payload, and reject cards without `confirmed_at`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_claim_card_store.py -v`

Expected: PASS.

### Task 3: Let candidate ranking accept the confirmed profile

**Files:**
- Modify: `clafact/kosis_candidate_search.py`
- Modify: `clafact/kosis_candidate_compat.py`
- Modify: `tests/test_kosis_candidate_search.py`

**Step 1: Write the failing test**

```python
def test_search_uses_explicit_confirmed_profile():
    profile = ClaimProfile(indicator="실업률", search_query="실업률", period="월")
    suggest_kosis_candidates("원문", FakeIndex(), profile=profile)
    assert index.last_query == "실업률"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_kosis_candidate_search.py -v`

Expected: FAIL because `profile` is not an accepted search argument.

**Step 3: Write minimal implementation**

Add optional explicit profile forwarding while preserving compatibility fallback for cached search callables.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_kosis_candidate_search.py -v`

Expected: PASS.

### Task 4: Connect the reviewed Claim Card to Shadow Mode

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write the failing UI-source regression test**

Assert that the Claim Card area is before KOSIS search, a card is stored through `ClaimCardStore`, and the KOSIS action requires a confirmed card.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -v`

Expected: FAIL because no Claim Card UI exists.

**Step 3: Write minimal implementation**

Display auto-extracted fields, explicitly save a reviewed card, use it for candidate discovery, and show a clear blocked message until it has been saved.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -v`

Expected: PASS.

### Task 5: Document and verify

**Files:**
- Create: `C:/Users/USER/Desktop/클라비_아이펠톤/ClaFact_완성형_핵심작업기록/05_Claim_표준구조화_규칙과_기술구현.md`

**Step 1: Write the implementation document**

Explain the exact input/output fields, rule sources, confirmation boundary, persistence location, and KOSIS handoff. Explicitly separate implemented behavior from future LLM enrichment.

**Step 2: Run complete verification**

Run: `python -m pytest -q`

Expected: all tests pass.

**Step 3: Commit**

```bash
git add clafact streamlit_app.py tests docs/plans/2026-08-03-claim-card-standard.md
git commit -m "feat: persist reviewed Claim Cards before KOSIS search"
```
