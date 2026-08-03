# Claim Context Inheritance and Selection Label Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Safely inherit one unambiguous article observation period into a selected Claim Card and make long multi-number sentence choices readable.

**Architecture:** A pure helper derives an article-level period only from strong temporal cues and reports the source row. The Claim Card receives that period only when its own parser found none. A pure label helper keeps the selectbox concise while preserving row identity and numeric-count context.

**Tech Stack:** Python, dataclasses, Streamlit, pytest.

---

### Task 1: Define safe context and label behavior with failing tests

**Files:**
- Create: `tests/test_claim_context.py`
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write failing tests**

```python
def test_unique_strong_article_period_is_available_to_later_sentence():
    context = resolve_article_period(["지난달 소비자물가가 2.4% 올랐다.", "배추는 -34.5%다."], "2025-11-04")
    assert context.period == "2025-10"
    assert context.row_index == 1

def test_conflicting_strong_periods_do_not_auto_inherit():
    context = resolve_article_period(["지난달 물가", "2025년 8월 물가"], "2025-11-04")
    assert context.period == ""
```

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_claim_context.py -v`

Expected: FAIL because helper does not exist.

### Task 2: Implement pure helpers

**Files:**
- Create: `clafact/claim_context.py`
- Test: `tests/test_claim_context.py`

**Step 1: Implement minimal code**

Normalize only absolute year-month and `지난달`/`이번달`; return a period only if unique. Build a label that identifies multi-number rows without changing their source sentence.

**Step 2: Run tests**

Run: `python -m pytest tests/test_claim_context.py -v`

Expected: PASS.

### Task 3: Connect helpers to Shadow Claim Card UI

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write failing source/UI regression test**

Assert the UI uses the compact sentence-label helper and forwards a unique article context period to Claim Card creation.

**Step 2: Implement minimal UI wiring**

Use the derived period only when `claim_card_draft.period` is empty. Display the inherited source row for reviewer audit. Do not enable a card when the article context is absent or conflicting.

**Step 3: Run UI tests**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py tests/test_claim_context.py -v`

Expected: PASS.

### Task 4: Verify and record

**Files:**
- Modify: `C:/Users/USER/Desktop/클라비_아이펠톤/ClaFact_완성형_핵심작업기록/00_프로젝트_문제_개선_이슈대장.md`

**Step 1: Run full suite**

Run: `python -m pytest -q`

Expected: PASS.

**Step 2: Commit and push**

```bash
git add clafact/claim_context.py streamlit_app.py tests docs/plans/
git commit -m "feat: inherit unambiguous Claim periods"
git push origin main
```
