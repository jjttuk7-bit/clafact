# Semantic 상태 보드 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Shadow Mode에서 현재 Semantic 검증 진행 상태와 다음 행동을 시각적으로 보여준다.

**Architecture:** 기존 `current_semantic_summary()` 집계값만 사용한다. `streamlit_app.py`에 표시 전용 상태 계산과 카드 HTML/CSS를 추가하고, Catalog·골든셋의 기존 집계 로직은 유지한다.

**Tech Stack:** Python, Streamlit, inline CSS, pytest

---

### Task 1: 상태 보드 화면 계약 테스트

**Files:**
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write the failing test**

5단계 이름, 다음 행동 문구, 상태 CSS 클래스와 Catalog·골든셋 분리 제목이 코드에 존재하는지 검증한다.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: FAIL because the current UI only prints flat metrics.

### Task 2: 진행 상태 보드 렌더링

**Files:**
- Modify: `streamlit_app.py:2038-2080`

**Step 1: Implement minimal UI**

- 5단계별 상태와 건수를 계산한다.
- `완료`·`현재 작업`·`대기` 카드와 연결 화살표를 렌더링한다.
- 첫 미완료 단계를 기준으로 다음 행동 문구를 렌더링한다.
- 기존 평면 `metric` 두 줄은 제거한다.

**Step 2: Run focused test**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: PASS.

### Task 3: 회귀 검증 및 커밋

**Files:**
- Modify: `docs/plans/2026-08-04-semantic-status-board-implementation.md`

**Step 1: Run full suite and syntax check**

Run: `python -m pytest -q; python -m py_compile streamlit_app.py`

Expected: PASS.

**Step 2: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_shadow_guide_safety.py docs/plans
git commit -m "feat: visualize semantic verification progress"
```
