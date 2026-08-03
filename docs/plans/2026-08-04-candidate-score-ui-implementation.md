# 후보 조건 충족도 표시 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** KOSIS 후보 점수의 계산 근거와 한계를 Shadow Mode 화면에서 재현 가능하게 표시한다.

**Architecture:** `streamlit_app.py`의 기존 후보 검색 결과를 그대로 사용한다. 점수 계산에는 손대지 않고, 같은 `confirmed_profile`과 Claim Card의 `subject`를 화면·탐색 이력에 함께 기록한다.

**Tech Stack:** Python, Streamlit, pytest

---

### Task 1: 화면 계약 테스트 추가

**Files:**
- Modify: `tests/test_streamlit_shadow_guide_safety.py`

**Step 1: Write the failing test**

후보 결과가 `후보 조건 충족도`, 실제 Claim 조건, 점수 한계 안내, `claim_subject` 이력 필드를 포함한다고 검증한다.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: FAIL because the current UI still says `적합도` and does not display the full trace.

### Task 2: 최소 화면·이력 변경

**Files:**
- Modify: `streamlit_app.py:2355-2409`

**Step 1: Implement**

- 후보 선택 라벨과 상세 제목을 `후보 조건 충족도 {fit_score}/100`으로 바꾼다.
- 후보 목록 위에 확정 Claim Card 기반 조건을 출력한다.
- 원점수·산정 내역·일치/감점 아래에 점수의 비판정 성격을 출력한다.
- 후보 이력 각 행에 `claim_subject`를 추가한다.

**Step 2: Run focused tests**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: PASS.

### Task 3: 전체 회귀 검증과 문서 상태 갱신

**Files:**
- Modify: `C:/Users/USER/Desktop/클라비_아이펠톤/ClaFact_완성형_핵심작업기록/00_프로젝트_문제_개선_이슈대장.md`

**Step 1: Update issue status**

ISS-006을 구현 완료·Cloud 화면 확인 대기로 갱신한다.

**Step 2: Run full suite**

Run: `python -m pytest -q`

Expected: PASS with no test failures.

**Step 3: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_shadow_guide_safety.py docs/plans
git commit -m "feat: explain KOSIS candidate score inputs"
```
