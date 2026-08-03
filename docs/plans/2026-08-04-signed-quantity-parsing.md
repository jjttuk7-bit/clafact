# Signed Quantity Parsing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve signed numeric values from a news sentence through `Quantity.raw`, `Quantity.value`, and `Quantity.normalized_value`.

**Architecture:** Extend only the number token in the existing `RE_QTY` parser. The parser will accept ASCII minus, Unicode minus, and plus, normalizing the parsed numeric value while retaining the source spelling in `raw`.

**Tech Stack:** Python, `re`, pytest.

---

### Task 1: Reproduce the signed-value failure

**Files:**
- Modify: `tests/test_parse.py`
- Modify: `tests/test_claim_card.py`

**Step 1: Write the failing tests**

```python
def test_extract_quantities_preserves_ascii_and_unicode_minus_signs():
    values = extract_quantities("배추(-34.5%), 무(−40.5%), 증가율은 +2.1%다.")
    assert [(q.raw, q.value) for q in values] == [
        ("-34.5%", -34.5), ("−40.5%", -40.5), ("+2.1%", 2.1),
    ]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_parse.py -v`

Expected: FAIL because the old expression drops the sign.

### Task 2: Preserve signs in the parser

**Files:**
- Modify: `clafact/pipeline/parse.py:22-88`
- Test: `tests/test_parse.py`

**Step 1: Implement the minimal parser change**

Add an optional leading sign capture to `RE_QTY`; normalize Unicode minus before calling `float`; retain the full original match for `raw`; apply scale to the signed number.

**Step 2: Run targeted tests**

Run: `python -m pytest tests/test_parse.py tests/test_claim_card.py -v`

Expected: PASS.

### Task 3: Verify and record the issue result

**Files:**
- Modify: `C:/Users/USER/Desktop/클라비_아이펠톤/ClaFact_완성형_핵심작업기록/00_프로젝트_문제_개선_이슈대장.md`

**Step 1: Run the full test suite**

Run: `python -m pytest -q`

Expected: PASS.

**Step 2: Update ISS-001**

Record the commit, tests, and new status only after successful verification.

**Step 3: Commit**

```bash
git add clafact/pipeline/parse.py tests/test_parse.py tests/test_claim_card.py docs/plans/
git commit -m "fix: preserve signs in numeric claims"
```
