# Review Queue Flow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 일반 KOSIS 판정과 공식 공지 Claim의 리뷰 행동을 분리하고, 승인 후 빈 리뷰 큐를 명확히 안내한다.

**Architecture:** Streamlit 리뷰 탭에서 기존 `source_type`으로 공식 공지 근거 입력을 조건부 렌더링한다. 승인·보류 뒤에는 세션 피드백을 남겨 재실행 후에도 완료 상태를 알리고, 빈 상태 메시지는 저장 큐와 세션 결과를 함께 고려한다.

**Tech Stack:** Python 3, Streamlit, pytest source-contract tests.

---

### Task 1: 리뷰 탭 화면 계약 테스트 추가

**Files:**
- Modify: `tests/test_upload_scoped_dashboard.py`
- Test: `tests/test_upload_scoped_dashboard.py`

**Step 1: Write the failing test**

```python
def test_reviewer_tab_separates_official_evidence_from_regular_approval():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    section = source[source.index('if view == "검증자 리뷰":'):source.index('# ═════════════ 탭 3: 플라이휠')]
    assert 'if row["source_type"] == "OFFICIAL_ANNOUNCEMENT":' in section
    assert 'st.session_state["review_feedback"]' in section
    assert "현재 검증자 리뷰 대기 항목이 없습니다." in section
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_upload_scoped_dashboard.py::test_reviewer_tab_separates_official_evidence_from_regular_approval -q`

Expected: FAIL because official-evidence inputs are unconditional and no post-review feedback exists.

**Step 3: Write minimal implementation**

No production change in this task.

**Step 4: Keep test red until Task 2**

### Task 2: 조건부 근거 입력과 승인 피드백 구현

**Files:**
- Modify: `streamlit_app.py:713-756`
- Test: `tests/test_upload_scoped_dashboard.py`

**Step 1: Implement the minimal review flow**

- Wrap official 기관명·URL·시행일·재검증 버튼 in `row["source_type"] == "OFFICIAL_ANNOUNCEMENT"`.
- On approve, save `"자동 판정을 승인했습니다."` in `st.session_state["review_feedback"]` before rerun.
- On hold, save `"판정을 보류했습니다."` in the same key.
- After loading the persisted queue, consume and show the feedback.
- If no persisted queue and no session results, show the new empty-queue message after feedback; show the generic first-verification guidance only when no feedback exists.

**Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_upload_scoped_dashboard.py::test_reviewer_tab_separates_official_evidence_from_regular_approval -q`

**Step 3: Run review-tab regression tests**

Run: `python -m pytest tests/test_upload_scoped_dashboard.py -q && python -m py_compile streamlit_app.py`

**Step 4: Commit**

```bash
git add streamlit_app.py tests/test_upload_scoped_dashboard.py
git commit -m "fix: clarify review queue approval flow"
```

### Task 3: Final verification

**Files:**
- Verify: `tests/test_upload_scoped_dashboard.py`, `tests/test_service.py`

**Step 1: Run focused tests**

Run: `python -m pytest tests/test_upload_scoped_dashboard.py tests/test_service.py -q`

**Step 2: Inspect changes**

Run: `git diff --check origin/main..HEAD && git status --short`

**Step 3: Commit plan**

```bash
git add docs/plans/2026-07-25-review-queue-flow.md
git commit -m "docs: plan review queue flow cleanup"
```
