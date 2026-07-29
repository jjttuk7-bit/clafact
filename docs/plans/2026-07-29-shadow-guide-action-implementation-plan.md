# Shadow Guide Action Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow Mode의 다섯 단계 가이드가 현재 단계와 다음 행동을 실제 화면 영역에 연결해 사용자가 순서대로 연구를 수행하게 한다.

**Architecture:** 순수 모듈 `clafact.shadow_step_guide`가 단계 상태와 화면 강조용 안내 모델을 만든다. `streamlit_app.py`는 저장된 Shadow 연구 기록을 읽어 이 모델을 렌더링만 하며, 운영 Claim·리뷰·판정에는 쓰지 않는다.

**Tech Stack:** Python 3.11, Streamlit, pytest, SQLite 연구 기록 저장소.

---

### Task 1: 화면 강조용 가이드 모델

**Files:**
- Modify: `clafact/shadow_step_guide.py`
- Test: `tests/test_shadow_step_guide.py`

**Step 1: Write the failing test**

```python
def test_guide_exposes_the_active_step_and_its_screen_hint():
    guide = build_shadow_step_guide(
        shadow_run={"rows": [{"row_index": 1}]}, selected_row_index=1,
    )

    assert guide.next_step_id == "find_candidate"
    assert guide.screen_hint.step_id == "find_candidate"
    assert "KOSIS 후보 3개 찾기" in guide.screen_hint.message
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shadow_step_guide.py::test_guide_exposes_the_active_step_and_its_screen_hint -q`

Expected: FAIL because `screen_hint` does not exist.

**Step 3: Write minimal implementation**

Add `ShadowGuideScreenHint(step_id, message)` and expose it on `ShadowStepGuide`. Map each next step to the label of the existing UI action.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shadow_step_guide.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/shadow_step_guide.py tests/test_shadow_step_guide.py
git commit -m "feat: expose Shadow guide screen hints"
```

### Task 2: Shadow Mode의 다음 행동 강조

**Files:**
- Modify: `streamlit_app.py:2276-2575`
- Test: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write the failing test**

```python
def test_shadow_mode_renders_the_current_guide_hint_near_candidate_actions():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    assert "guide.screen_hint.message" in source
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: FAIL because the current guide has no screen hint.

**Step 3: Write minimal implementation**

Render an `st.info` message immediately before the matching existing workflow area: candidate search, KOSIS mapping/value comparison, or Shadow review/export. Do not add a new persistence store and do not alter existing buttons.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py tests/test_shadow_step_guide.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_shadow_guide_safety.py
git commit -m "feat: highlight the next Shadow workflow action"
```

### Task 3: End-to-end verification and release

**Files:**
- Verify: `streamlit_app.py`
- Verify: `tests/test_shadow_step_guide.py`
- Verify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Run focused tests**

Run: `python -m pytest tests/test_shadow_step_guide.py tests/test_streamlit_shadow_guide_safety.py tests/test_kosis_candidate_search.py tests/test_kosis_mapping.py -q`

Expected: PASS.

**Step 2: Verify the Streamlit application starts**

Run:

```bash
python -m py_compile streamlit_app.py
python -c "from streamlit.testing.v1 import AppTest; app=AppTest.from_file('streamlit_app.py'); app.run(timeout=60); assert not app.exception; print('Streamlit AppTest: OK')"
```

Expected: `Streamlit AppTest: OK`.

**Step 3: Commit and publish**

```bash
git add docs/plans/2026-07-29-shadow-guide-action-*.md
git commit -m "docs: plan Shadow guide action flow"
git checkout main
git merge --ff-only feature/kosis-evidence-object
git push origin main
```
