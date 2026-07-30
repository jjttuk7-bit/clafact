# Multicultural Marriage Verification Implementation Plan

| 항목 | 내용 |
|---|---|
| Author | Unattributed draft (provenance unverified) |
| Reviewed by | ClaFact Hermes Agent |
| Managed by | ClaFact Hermes Agent |
| Status | Superseded |
| Version | v0.2 |
| Last Updated | 2026-07-30 |

> **Status note:** This plan is retained as a historical record. It was superseded by commit `f26407f` (`feat: verify registered multicultural share metrics`), whose implementation uses `official_share_metrics.json`, `tests/test_run.py`, and `tests/test_service.py`, and additionally supports multicultural-birth share claims.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Verify annual multicultural-marriage share claims from official marriage-count evidence.

**Architecture:** Add a focused derived-ratio verifier that recognizes the multicultural-marriage-share claim, retrieves yearly numerator and denominator values from fixture evidence, and records an audit trail for both success and failure. Keep the existing generic verifier unchanged for all other claims.

**Tech Stack:** Python, pytest, JSON fixtures

---

### Task 1: Add a failing regression test

**Files:**
- Modify: `tests/test_verdict.py`

**Step 1:** Add a claim for 2024 multicultural-marriage share of 9.6% and a 1.0 percentage-point decline.

**Step 2:** Assert `match`, calculation evidence, and a non-empty audit trail.

**Step 3:** Run the focused test and confirm it fails before production changes.

### Task 2: Add official fixture evidence and a focused verifier

**Files:**
- Modify: `data/samples/kosis/tables_meta.json`
- Modify: `data/samples/kosis/*.json`
- Modify: `clafact/pipeline/run.py`

**Step 1:** Add table metadata and annual values for multicultural and total marriages.

**Step 2:** Implement only the derived-share calculation required by the regression test.

**Step 3:** Preserve the source data and calculation in the audit trail.

### Task 3: Verify the change

**Files:**
- Verify: `tests/test_verdict.py`

**Step 1:** Run the focused regression test.

**Step 2:** Run the verdict test module.

**Step 3:** Run the complete test suite.
