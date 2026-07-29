# Shadow Mode Step Guide Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show a five-step, state-driven usage guide for the research-only Shadow Mode workflow.

**Architecture:** Add a pure helper that derives five guide steps from existing Shadow, candidate-search, evidence-mapping, numerical-comparison, and review records. The Streamlit page renders the helper output above the existing controls without disabling any controls or mutating operating verdicts.

**Tech Stack:** Python 3.11, Streamlit, SQLite-backed research stores, pytest, Streamlit AppTest.

---

### Task 1: Derive guide state from research records

**Files:**
- Create: `clafact/shadow_step_guide.py`
- Create: `tests/test_shadow_step_guide.py`

**Step 1: Write the failing test**

Test no-run, fresh-run, mapped-evidence, numerical-match, and review-complete inputs. Assert the five ordered steps, completed count, and first next action.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shadow_step_guide.py -q`  
Expected: import error because the helper does not exist.

**Step 3: Write minimal implementation**

Implement `build_shadow_step_guide(...)` returning step id, label, state, detail, and `next_step_id`. Treat `not_comparable` numerical results as review-needed, not completion.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shadow_step_guide.py -q`  
Expected: all tests pass.

### Task 2: Render the guide above Shadow controls

**Files:**
- Modify: `streamlit_app.py` near the Shadow Mode heading and persisted-run loading
- Test: `tests/test_shadow_step_guide.py`

**Step 1: Write a failing UI-contract test**

Add a test for guide display labels and next-action text in the pure helper.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shadow_step_guide.py -q`

**Step 3: Write minimal implementation**

Load only the research records for the current Shadow run, call the helper, and render `연구 진행 가이드`, completion count, step rows, and the one next action. Do not add button disabling or operating-store writes.

**Step 4: Run tests and AppTest**

Run:
`python -m pytest tests/test_shadow_step_guide.py tests/test_shadow_service.py tests/test_shadow_export.py -q`

Run:
`python -c "from streamlit.testing.v1 import AppTest; app=AppTest.from_file('streamlit_app.py'); app.run(timeout=60); assert not app.exception"`

### Task 3: Verify and deliver

**Files:**
- Modify only files from Tasks 1–2.

**Step 1: Run focused regression suite**

Run:
`python -m pytest tests/test_shadow_step_guide.py tests/test_kosis_value_comparison.py tests/test_kosis_value_comparison_store.py tests/test_shadow_export.py tests/test_shadow_service.py -q`

**Step 2: Compile**

Run: `python -m py_compile streamlit_app.py clafact/shadow_step_guide.py`

**Step 3: Commit and push**

Run:
`git add ... && git commit -m "feat: guide Shadow Mode workflow" && git push origin feature/kosis-evidence-object`

Fast-forward `main` and push it after all verification passes.
